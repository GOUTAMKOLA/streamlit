/**
 * Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2025)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import React, { FC, memo, useEffect, useId, useMemo, useRef } from "react"

import { getLogger } from "loglevel"

import { BidiComponent as BidiComponentProto } from "@streamlit/protobuf"

const LOG = getLogger("BidiComponent")

export type BidiComponentProps = {
  element: BidiComponentProto
}

interface UseShadowDomResult {
  containerRef: React.RefObject<HTMLDivElement>
  shadowRootRef: React.RefObject<ShadowRoot | null>
}

const useShadowDom = (
  id: string,
  isolateStyles: boolean
): UseShadowDomResult => {
  const containerRef = useRef<HTMLDivElement>(null)
  const shadowRootRef = useRef<ShadowRoot | null>(null)

  useEffect(() => {
    if (!containerRef.current) {
      return
    }

    const containerElement = containerRef.current

    // Create shadow root if isolateStyles is true
    if (isolateStyles && !shadowRootRef.current) {
      try {
        shadowRootRef.current = containerElement.attachShadow({ mode: "open" })
      } catch (error) {
        LOG.error(
          `BidiComponent Error: Failed to create shadow DOM for element ${id}`,
          error
        )
      }
    }
  }, [id, isolateStyles])

  return { containerRef, shadowRootRef }
}

const useHtmlCssContent = ({
  isolateStyles,
  html,
  css,
  containerRef,
  shadowRootRef,
}: {
  isolateStyles: boolean
  html: string
  css: string
  containerRef: React.RefObject<HTMLDivElement>
  shadowRootRef: React.RefObject<ShadowRoot | null>
}): void => {
  const contentContainerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!containerRef.current) {
      return
    }

    // Determine parent element (shadow root or container)
    const parent =
      isolateStyles && shadowRootRef.current
        ? shadowRootRef.current
        : containerRef.current

    // Clean up previous content
    if (
      contentContainerRef.current &&
      contentContainerRef.current.parentNode === parent
    ) {
      parent.removeChild(contentContainerRef.current)
    }

    // Create content container if needed
    if (html || css) {
      contentContainerRef.current = document.createElement("div")

      // Add HTML content if available
      if (html) {
        const htmlDiv = document.createElement("div")
        htmlDiv.innerHTML = html
        contentContainerRef.current.appendChild(htmlDiv)
      }

      // Add CSS content if available
      if (css) {
        const styleElement = document.createElement("style")
        styleElement.textContent = css
        contentContainerRef.current.appendChild(styleElement)
      }

      parent.appendChild(contentContainerRef.current)
    }
  }, [isolateStyles, html, css, containerRef, shadowRootRef])
}

const useJavaScriptContent = ({
  id,
  jsContent,
  isolateStyles,
  componentId,
  containerRef,
  shadowRootRef,
}: {
  id: string
  jsContent: string
  isolateStyles: boolean
  componentId: string
  containerRef: React.RefObject<HTMLDivElement>
  shadowRootRef: React.RefObject<ShadowRoot | null>
}): void => {
  useEffect(() => {
    if (!jsContent) {
      LOG.error("BidiComponent Error: No JavaScript content provided.")
      return
    }

    if (!containerRef.current) {
      LOG.error("BidiComponent Error: No container element provided.")
      return
    }

    // Track mounted state to prevent race conditions
    let isMounted = true

    // Construct a data URI for the JavaScript content
    const dataUri = `data:text/javascript;charset=utf-8,${encodeURIComponent(
      jsContent
    )}`

    // Store cleanup function from module if provided
    // NOTE: This is a modification from the spec to allow for a cleanup function
    // to be returned from the module.
    let cleanup: (() => void) | undefined

    const handleImport = async (): Promise<void> => {
      try {
        // Dynamically import the module from the data URI
        const module = await import(/* @vite-ignore */ dataUri)

        // Check if component is still mounted before continuing
        if (!isMounted) {
          return
        }

        if (module.default && typeof module.default === "function") {
          // Determine parent element (shadow root or container)
          const parentElement =
            isolateStyles && shadowRootRef.current
              ? shadowRootRef.current
              : containerRef.current

          const result = module.default({
            // TODO: Add a name
            name: "",
            // TODO: Add data
            data: null,
            key: componentId,
            parentElement,
            // TODO: Add child container IDs
            childContainerIDs: [],
          })

          // If the module returns a cleanup function, store it
          if (typeof result === "function") {
            cleanup = result
          }
        } else {
          LOG.error(
            "BidiComponent Error: Module does not have a default export function.",
            id
          )
        }
      } catch (error) {
        // Check if component is still mounted before logging errors
        if (isMounted) {
          LOG.error(
            `BidiComponent Error: Failed to load or execute script for element ${id}`,
            error
          )
        }
      }
    }

    handleImport()

    return () => {
      // Set mounted state to false first
      isMounted = false

      if (!cleanup) {
        return
      }

      try {
        cleanup()
      } catch (error) {
        LOG.error(
          `BidiComponent Error: Failed to run cleanup for element ${id}`,
          error
        )
      }
    }

    // NOTE: Intentionally only running on mount in order to achieve the product behavior of
    // not allowing `jsContent` to be updated after the component is mounted.
    // eslint-disable-next-line react-compiler/react-compiler
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}

const useProcessBidiElement = (
  element: BidiComponentProto
): { html: string; css: string } => {
  const { htmlContent, cssContent } = element

  const userHtmlContent = useMemo(() => htmlContent.trim(), [htmlContent])

  const userCssContent = useMemo(() => cssContent.trim(), [cssContent])

  return {
    html: userHtmlContent,
    css: userCssContent,
  }
}

const BidiComponent: FC<BidiComponentProps> = ({ element }) => {
  const { id, jsContent, isolateStyles } = element

  const { html, css } = useProcessBidiElement(element)
  const { containerRef, shadowRootRef } = useShadowDom(id, isolateStyles)
  const componentId = useId()

  useHtmlCssContent({ isolateStyles, html, css, containerRef, shadowRootRef })

  useJavaScriptContent({
    id,
    jsContent,
    isolateStyles,
    componentId,
    containerRef,
    shadowRootRef,
  })

  return <div ref={containerRef} data-testid="stBidiComponent" />
}

export default memo(BidiComponent)

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

// Component for isolated styles (shadow DOM)
const IsolatedComponent: FC<{
  id: string
  jsContent: string
  htmlContent: string
  cssContent: string
}> = ({ id, jsContent, htmlContent: html, cssContent }) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const shadowRootRef = useRef<ShadowRoot | null>(null)
  const contentRef = useRef<HTMLDivElement | null>(null)
  const componentId = useId()

  // Create shadow DOM once when component mounts
  useEffect(() => {
    if (!containerRef.current) {
      return
    }

    try {
      shadowRootRef.current = containerRef.current.attachShadow({
        mode: "open",
      })
    } catch (error) {
      LOG.error(
        `BidiComponent Error: Failed to create shadow DOM for element ${id}`,
        error
      )
    }
  }, [id])

  // Handle HTML and CSS content
  useEffect(() => {
    if (!shadowRootRef.current) {
      return
    }

    // Clean up previous content
    if (
      contentRef.current &&
      contentRef.current.parentNode === shadowRootRef.current
    ) {
      shadowRootRef.current.removeChild(contentRef.current)
    }

    // Create new content container
    contentRef.current = document.createElement("div")

    // Add HTML content if available
    if (html) {
      const htmlDiv = document.createElement("div")
      htmlDiv.innerHTML = html
      contentRef.current.appendChild(htmlDiv)
    }

    // Add CSS content if available
    if (cssContent) {
      const styleElement = document.createElement("style")
      styleElement.textContent = cssContent
      contentRef.current.appendChild(styleElement)
    }

    shadowRootRef.current.appendChild(contentRef.current)
  }, [html, cssContent])

  // Handle JavaScript content
  useEffect(() => {
    if (!jsContent || !shadowRootRef.current) {
      return
    }

    let isMounted = true
    let cleanup: (() => void) | undefined

    const dataUri = `data:text/javascript;charset=utf-8,${encodeURIComponent(
      jsContent
    )}`

    const handleImport = async (): Promise<void> => {
      try {
        const module = await import(/* @vite-ignore */ dataUri)

        if (!isMounted || !shadowRootRef.current) {
          return
        }

        if (module.default && typeof module.default === "function") {
          const result = module.default({
            name: "",
            data: null,
            key: componentId,
            parentElement: shadowRootRef.current,
            childContainerIDs: [],
          })

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
      isMounted = false
      if (cleanup) {
        try {
          cleanup()
        } catch (error) {
          LOG.error(
            `BidiComponent Error: Failed to run cleanup for element ${id}`,
            error
          )
        }
      }
    }
    // NOTE: Intentionally only running on mount to achieve product behavior
    // eslint-disable-next-line react-compiler/react-compiler
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return <div ref={containerRef} data-testid="stBidiComponent-isolated" />
}

// Component for non-isolated styles (regular DOM)
const NonIsolatedComponent: FC<{
  id: string
  jsContent: string
  htmlContent: string
  cssContent: string
}> = ({ id, jsContent, htmlContent: html, cssContent }) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement | null>(null)
  const componentId = useId()

  // Handle HTML and CSS content
  useEffect(() => {
    if (!containerRef.current) {
      return
    }

    // Clean up previous content
    if (
      contentRef.current &&
      contentRef.current.parentNode === containerRef.current
    ) {
      containerRef.current.removeChild(contentRef.current)
    }

    // Create new content container
    contentRef.current = document.createElement("div")

    // Add HTML content if available
    if (html) {
      const htmlDiv = document.createElement("div")
      htmlDiv.innerHTML = html
      contentRef.current.appendChild(htmlDiv)
    }

    // Add CSS content if available
    if (cssContent) {
      const styleElement = document.createElement("style")
      styleElement.textContent = cssContent
      contentRef.current.appendChild(styleElement)
    }

    containerRef.current.appendChild(contentRef.current)
  }, [html, cssContent])

  // Handle JavaScript content
  useEffect(() => {
    if (!jsContent || !containerRef.current) {
      return
    }

    // Track mounted state to prevent race conditions
    let isMounted = true
    // Store cleanup function from module if provided
    // NOTE: This is a modification from the spec to allow for a cleanup function
    // to be returned from the module.
    let cleanup: (() => void) | undefined

    // Construct a data URI for the JavaScript content
    const dataUri = `data:text/javascript;charset=utf-8,${encodeURIComponent(
      jsContent
    )}`

    const handleImport = async (): Promise<void> => {
      try {
        // Dynamically import the module from the data URI
        const module = await import(/* @vite-ignore */ dataUri)

        // Check if component is still mounted before continuing
        if (!isMounted || !containerRef.current) {
          return
        }

        if (module.default && typeof module.default === "function") {
          const result = module.default({
            // TODO: Add a name
            name: "",
            // TODO: Add data
            data: null,
            key: componentId,
            parentElement: containerRef.current,
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

  return <div ref={containerRef} data-testid="stBidiComponent-regular" />
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

  // Render either isolated or non-isolated component based on isolateStyles flag
  return isolateStyles ? (
    <IsolatedComponent
      cssContent={css}
      htmlContent={html}
      id={id}
      jsContent={jsContent}
    />
  ) : (
    <NonIsolatedComponent
      cssContent={css}
      htmlContent={html}
      id={id}
      jsContent={jsContent}
    />
  )
}

export default memo(BidiComponent)

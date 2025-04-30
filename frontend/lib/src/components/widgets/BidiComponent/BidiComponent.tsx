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

const useHandleHtmlAndCssContent = ({
  containerRef,
  html,
  cssContent,
  isShadowRoot,
  skip = false,
}: {
  containerRef: React.RefObject<HTMLDivElement>
  html: string
  cssContent: string
  isShadowRoot: boolean
  skip?: boolean
}): React.MutableRefObject<HTMLDivElement | null> => {
  const contentRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (skip || !containerRef.current) {
      return
    }

    const parent = isShadowRoot
      ? containerRef.current.shadowRoot
      : containerRef.current

    if (!parent) {
      return
    }

    // Clean up previous content
    if (contentRef.current && contentRef.current.parentNode === parent) {
      parent.removeChild(contentRef.current)
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

    parent.appendChild(contentRef.current)
  }, [html, cssContent, containerRef, isShadowRoot, skip])

  return contentRef
}

const useHandleJsContent = ({
  jsContent,
  id,
  parentRef,
  skip = false,
}: {
  jsContent: string
  id: string
  parentRef: React.RefObject<HTMLDivElement | ShadowRoot | null>
  skip?: boolean
}): void => {
  const componentId = `st-bidi-component-${useId()}`

  useEffect(() => {
    if (skip || !jsContent || !parentRef.current) {
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

        if (!isMounted || !parentRef.current) {
          return
        }

        if (module.default && typeof module.default === "function") {
          const result = module.default({
            name: "",
            data: null,
            key: componentId,
            parentElement: parentRef.current,
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
  }, [skip])
}

const IsolatedComponent: FC<{
  id: string
  jsContent: string
  htmlContent: string
  cssContent: string
}> = ({ id, jsContent, htmlContent: html, cssContent }) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const shadowRootRef = useRef<ShadowRoot | null>(null)
  const [isShadowRootReady, setIsShadowRootReady] = React.useState(false)

  useEffect(() => {
    if (!containerRef.current) {
      return
    }

    // Don't try to attach a shadow root if the element already has one
    if (containerRef.current.shadowRoot) {
      shadowRootRef.current = containerRef.current.shadowRoot
      setIsShadowRootReady(true)
      return
    }

    try {
      shadowRootRef.current = containerRef.current.attachShadow({
        mode: "open",
      })
      setIsShadowRootReady(true)
    } catch (error) {
      LOG.error(
        `BidiComponent Error: Failed to create shadow DOM for element ${id}`,
        error
      )
    }
  }, [id])

  useHandleHtmlAndCssContent({
    containerRef,
    html,
    cssContent,
    isShadowRoot: true,
    skip: !isShadowRootReady,
  })

  useHandleJsContent({
    jsContent,
    id,
    parentRef: shadowRootRef,
    skip: !isShadowRootReady,
  })

  return <div ref={containerRef} data-testid="stBidiComponent-isolated" />
}

const NonIsolatedComponent: FC<{
  id: string
  jsContent: string
  htmlContent: string
  cssContent: string
}> = ({ id, jsContent, htmlContent: html, cssContent }) => {
  const containerRef = useRef<HTMLDivElement>(null)

  useHandleHtmlAndCssContent({
    containerRef,
    html,
    cssContent,
    isShadowRoot: false,
  })

  useHandleJsContent({
    jsContent,
    id,
    parentRef: containerRef,
  })

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

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

const getUrlForSourcePath = (sourcePath: string): string => {
  // TODO: Make this dynamic to support SiS usecases
  return `bidi_components/${sourcePath}`
}

export type BidiComponentProps = {
  element: BidiComponentProto
}

const useHandleHtmlAndCssContent = ({
  containerRef,
  html,
  cssContent,
  isShadowRoot,
  skip = false,
  cssSourcePath,
}: {
  containerRef: React.RefObject<HTMLDivElement>
  html: string | undefined
  cssContent: string | undefined
  isShadowRoot: boolean
  skip?: boolean
  cssSourcePath: string | undefined
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
    } else if (cssSourcePath) {
      const linkElement = document.createElement("link")
      linkElement.href = getUrlForSourcePath(cssSourcePath)
      linkElement.rel = "stylesheet"
      contentRef.current.appendChild(linkElement)
    }

    parent.appendChild(contentRef.current)
  }, [html, cssContent, containerRef, isShadowRoot, skip, cssSourcePath])

  return contentRef
}

const useHandleJsContent = ({
  jsContent,
  id,
  parentRef,
  skip = false,
  data,
  jsSourcePath,
}: {
  jsContent: string | undefined
  id: string
  parentRef: React.RefObject<HTMLDivElement | ShadowRoot | null>
  skip?: boolean
  data: string | undefined
  jsSourcePath: string | undefined
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
            data: data ? JSON.parse(data) : null,
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

  useEffect(() => {
    if (skip || !jsSourcePath) {
      return
    }

    const scriptElement = document.createElement("script")
    scriptElement.src = getUrlForSourcePath(jsSourcePath)
    document.head.appendChild(scriptElement)
  }, [jsSourcePath, skip])
}

const IsolatedComponent: FC<{
  id: string
  jsContent: string | undefined
  htmlContent: string | undefined
  cssContent: string | undefined
  data: string | undefined
  jsSourcePath: string | undefined
  cssSourcePath: string | undefined
}> = ({
  id,
  jsContent,
  htmlContent: html,
  cssContent,
  data,
  jsSourcePath,
  cssSourcePath,
}) => {
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
    cssContent,
    cssSourcePath,
    html,
    isShadowRoot: true,
    skip: !isShadowRootReady,
  })

  useHandleJsContent({
    data,
    id,
    jsContent,
    jsSourcePath,
    parentRef: shadowRootRef,
    skip: !isShadowRootReady,
  })

  return <div ref={containerRef} data-testid="stBidiComponent-isolated" />
}

const NonIsolatedComponent: FC<{
  cssContent: string | undefined
  cssSourcePath: string | undefined
  data: string | undefined
  htmlContent: string | undefined
  id: string
  jsContent: string | undefined
  jsSourcePath: string | undefined
}> = ({
  cssContent,
  cssSourcePath,
  data,
  htmlContent: html,
  id,
  jsContent,
  jsSourcePath,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)

  useHandleHtmlAndCssContent({
    containerRef,
    cssContent,
    cssSourcePath,
    html,
    isShadowRoot: false,
  })

  useHandleJsContent({
    data,
    id,
    jsContent,
    jsSourcePath,
    parentRef: containerRef,
  })

  return <div ref={containerRef} data-testid="stBidiComponent-regular" />
}

const useProcessBidiElement = (
  element: BidiComponentProto
): { html: string | undefined; css: string | undefined } => {
  const { htmlContent, cssContent } = element

  const userHtmlContent = useMemo(() => htmlContent?.trim(), [htmlContent])
  const userCssContent = useMemo(() => cssContent?.trim(), [cssContent])

  return {
    html: userHtmlContent,
    css: userCssContent,
  }
}

const BidiComponent: FC<BidiComponentProps> = ({ element }) => {
  const { cssSourcePath, data, id, isolateStyles, jsContent, jsSourcePath } =
    element

  const { html, css } = useProcessBidiElement(element)

  // Render either isolated or non-isolated component based on isolateStyles flag
  return isolateStyles ? (
    <IsolatedComponent
      cssContent={css}
      cssSourcePath={cssSourcePath ?? undefined}
      data={data}
      htmlContent={html}
      id={id}
      jsContent={jsContent ?? undefined}
      jsSourcePath={jsSourcePath ?? undefined}
    />
  ) : (
    <NonIsolatedComponent
      cssContent={css}
      cssSourcePath={cssSourcePath ?? undefined}
      data={data}
      htmlContent={html}
      id={id}
      jsContent={jsContent ?? undefined}
      jsSourcePath={jsSourcePath ?? undefined}
    />
  )
}

export default memo(BidiComponent)

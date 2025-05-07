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

import type { BidiComponent as BidiComponentProto } from "@streamlit/protobuf"

import type { WidgetStateManager } from "src/WidgetStateManager"

const LOG = getLogger("BidiComponent")

const getUrlForSourcePath = (sourcePath: string): string => {
  return `/bidi_components/${sourcePath}`
}

export type BidiComponentProps = {
  element: BidiComponentProto
  widgetMgr: WidgetStateManager
}

const useHandleHtmlAndCssContent = ({
  containerRef,
  html,
  cssContent,
  skip = false,
  cssSourcePath,
}: {
  containerRef: React.RefObject<HTMLElement | ShadowRoot>
  html: string | undefined
  cssContent: string | undefined
  skip?: boolean
  cssSourcePath: string | undefined
}): React.MutableRefObject<HTMLDivElement | null> => {
  const contentRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const parent = containerRef.current

    if (skip || !parent) {
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
  }, [html, cssContent, containerRef, skip, cssSourcePath])

  return contentRef
}

const importAndRunModule = async ({
  moduleUrl,
  id,
  parentRef,
  data,
  componentId,
  widgetMgr,
  onError,
}: {
  moduleUrl: string
  id: string
  parentRef: React.RefObject<HTMLDivElement | ShadowRoot | null>
  data: string | undefined
  componentId: string
  widgetMgr: WidgetStateManager
  onError: (error: unknown) => void
}): Promise<(() => void) | undefined> => {
  try {
    const module = await import(/* @vite-ignore */ moduleUrl)
    if (
      module.default &&
      typeof module.default === "function" &&
      parentRef.current
    ) {
      const result = module.default({
        name: "",
        data: data ? JSON.parse(data) : null,
        key: componentId,
        parentElement: parentRef.current,
        childContainerIDs: [],
        onChange: (value: unknown) => {
          widgetMgr.setJsonValue({ id }, value, { fromUi: true }, undefined)
        },
      })
      if (typeof result === "function") {
        return result
      }
    } else {
      onError("Module does not have a default export function.")
    }
  } catch (error) {
    onError(error)
  }
}

const useHandleJsContent = ({
  jsContent,
  id,
  parentRef,
  skip = false,
  data,
  jsSourcePath,
  widgetMgr,
}: {
  jsContent: string | undefined
  id: string
  parentRef: React.RefObject<HTMLDivElement | ShadowRoot | null>
  skip?: boolean
  data: string | undefined
  jsSourcePath: string | undefined
  widgetMgr: WidgetStateManager
}): void => {
  const componentId = `st-bidi-component-${useId()}`

  useEffect(() => {
    if (skip || (!jsContent && !jsSourcePath) || !parentRef.current) {
      return
    }

    let isMounted = true
    let cleanup: (() => void) | undefined
    let scriptElement: HTMLScriptElement | undefined

    const onError = (error: unknown): void => {
      if (isMounted) {
        LOG.error(
          `BidiComponent Error: Failed to load or execute script for element ${id}`,
          error
        )
      }
    }

    const run = async (): Promise<void> => {
      try {
        if (jsContent) {
          const dataUri = `data:text/javascript;charset=utf-8,${encodeURIComponent(
            jsContent
          )}`

          cleanup = await importAndRunModule({
            moduleUrl: dataUri,
            id,
            parentRef,
            data,
            componentId,
            widgetMgr,
            onError,
          })
        } else if (jsSourcePath) {
          const scriptUrl = getUrlForSourcePath(jsSourcePath)
          scriptElement = document.createElement("script")
          scriptElement.type = "module"
          scriptElement.src = scriptUrl
          scriptElement.async = true

          // Wait for script to load or error
          await new Promise<void>((resolve, reject) => {
            if (!scriptElement) {
              reject(new Error("Script element not found"))
              return
            }

            scriptElement.onload = () => resolve()
            scriptElement.onerror = () =>
              reject(new Error("Script load error"))

            document.head.appendChild(scriptElement)
          })

          cleanup = await importAndRunModule({
            moduleUrl: scriptUrl,
            id,
            parentRef,
            data,
            componentId,
            widgetMgr,
            onError,
          })
        }
      } catch (error) {
        onError(error)
      }
    }

    run()

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
      if (scriptElement && scriptElement.parentNode) {
        scriptElement.parentNode.removeChild(scriptElement)
      }
    }
    // eslint-disable-next-line react-compiler/react-compiler
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skip])
}

const IsolatedComponent: FC<{
  id: string
  jsContent: string | undefined
  htmlContent: string | undefined
  cssContent: string | undefined
  data: string | undefined
  jsSourcePath: string | undefined
  cssSourcePath: string | undefined
  widgetMgr: WidgetStateManager
}> = ({
  id,
  jsContent,
  htmlContent: html,
  cssContent,
  data,
  jsSourcePath,
  cssSourcePath,
  widgetMgr,
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
    containerRef: shadowRootRef,
    cssContent,
    cssSourcePath,
    html,
    skip: !isShadowRootReady,
  })

  useHandleJsContent({
    data,
    id,
    jsContent,
    jsSourcePath,
    parentRef: shadowRootRef,
    skip: !isShadowRootReady,
    widgetMgr,
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
  widgetMgr: WidgetStateManager
}> = ({
  cssContent,
  cssSourcePath,
  data,
  htmlContent: html,
  id,
  jsContent,
  jsSourcePath,
  widgetMgr,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)

  useHandleHtmlAndCssContent({
    containerRef,
    cssContent,
    cssSourcePath,
    html,
  })

  useHandleJsContent({
    data,
    id,
    jsContent,
    jsSourcePath,
    parentRef: containerRef,
    widgetMgr,
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

const BidiComponent: FC<BidiComponentProps> = ({ element, widgetMgr }) => {
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
      widgetMgr={widgetMgr}
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
      widgetMgr={widgetMgr}
    />
  )
}

export default memo(BidiComponent)

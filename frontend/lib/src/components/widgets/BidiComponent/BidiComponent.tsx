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

import React, { FC, memo, useEffect, useId, useRef, useState } from "react"

import { getLogger } from "loglevel"

import type { BidiComponent as BidiComponentProto } from "@streamlit/protobuf"

import type { WidgetStateManager } from "src/WidgetStateManager"
import ErrorElement from "~lib/components/shared/ErrorElement"
import type { ComponentResult, StBidiComponentV2Args } from "./types"

const LOG = getLogger("BidiComponent")

const getUrlForSourcePath = (sourcePath: string): string => {
  return `/bidi_components/${sourcePath}`
}

export type BidiComponentProps = {
  element: BidiComponentProto
  widgetMgr: WidgetStateManager
}

/**
 * Normalize errors to a standard Error object
 */
const normalizeError = (error: unknown, context?: string): Error => {
  if (error instanceof Error) {
    return error
  }

  const message = context ? `${context}: ${String(error)}` : String(error)
  return new Error(message)
}

/**
 * Centralized error handler to log and set error state
 */
const handleError = (
  error: unknown,
  setError: (error: Error) => void,
  context?: string
): void => {
  const normalizedError = normalizeError(error, context)
  LOG.error(`BidiComponent Error: ${normalizedError.message}`, error)
  setError(normalizedError)
}

const useHandleHtmlAndCssContent = ({
  containerRef,
  cssContent,
  cssSourcePath,
  html,
  setError,
  skip = false,
}: {
  containerRef: React.RefObject<HTMLElement | ShadowRoot>
  cssContent: string | undefined
  cssSourcePath: string | undefined
  html: string | undefined
  setError: (error: Error) => void
  skip?: boolean
}): React.MutableRefObject<HTMLDivElement | null> => {
  const contentRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (skip) {
      return
    }

    const parent = containerRef.current
    if (!parent) {
      return
    }

    try {
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
        linkElement.onerror = () => {
          handleError(`Failed to load CSS from ${cssSourcePath}`, setError)
        }
        contentRef.current.appendChild(linkElement)
      }

      parent.appendChild(contentRef.current)
    } catch (error) {
      handleError(error, setError, "Failed to process HTML/CSS content")
    }
  }, [html, cssContent, containerRef, cssSourcePath, setError, skip])

  return contentRef
}

const loadAndRunModule = async ({
  componentId,
  componentIdForWidgetMgr,
  componentName,
  data,
  moduleUrl,
  parentElement,
  widgetMgr,
}: {
  componentId: string
  componentIdForWidgetMgr: string
  componentName: string
  data: unknown
  moduleUrl: string
  parentElement: HTMLElement | ShadowRoot
  widgetMgr: WidgetStateManager
}): Promise<ComponentResult> => {
  const module = await import(/* @vite-ignore */ moduleUrl)

  if (!module) {
    throw new Error("JS module does not exist.")
  }

  if (!module.default || typeof module.default !== "function") {
    throw new Error("JS module does not have a default export function.")
  }

  const cleanup = module.default({
    name: componentName,
    data,
    // TODO: We should not pass `key`, since React gives a warning, since `key`
    // is a reserved prop.
    key: componentId,
    parentElement,
    // TODO: FIXME:
    childContainerIDs: [],
    onChange: (value: unknown) => {
      widgetMgr.setJsonValue(
        { id: componentIdForWidgetMgr },
        value,
        { fromUi: true },
        undefined
      )
    },
  } satisfies StBidiComponentV2Args)

  return {
    cleanup: typeof cleanup === "function" ? cleanup : undefined,
  }
}

const useHandleJsContent = ({
  componentName,
  data,
  id,
  jsContent,
  jsSourcePath,
  parentRef,
  setError,
  skip = false,
  widgetMgr,
}: {
  componentName: string
  data: string | undefined
  id: string
  jsContent: string | undefined
  jsSourcePath: string | undefined
  parentRef: React.RefObject<HTMLElement | ShadowRoot>
  setError: (error: Error) => void
  skip?: boolean
  widgetMgr: WidgetStateManager
}): void => {
  const componentId = `st-bidi-component-${useId()}`

  useEffect(() => {
    if (skip || (!jsContent && !jsSourcePath) || !parentRef.current) {
      return
    }

    let isMounted = true
    let cleanup: ComponentResult["cleanup"]
    let scriptElement: HTMLScriptElement | undefined

    const parsedData = data ? JSON.parse(data) : null

    const run = async (): Promise<void> => {
      try {
        // Handle inline JS content
        if (jsContent) {
          const dataUri = `data:text/javascript;charset=utf-8,${encodeURIComponent(
            jsContent
          )}`

          const result = await loadAndRunModule({
            componentName,
            moduleUrl: dataUri,
            componentId,
            parentElement: parentRef.current!,
            data: parsedData,
            componentIdForWidgetMgr: id,
            widgetMgr,
          })

          cleanup = result.cleanup
        }
        // Handle external JS file
        else if (jsSourcePath) {
          const scriptUrl = getUrlForSourcePath(jsSourcePath)

          try {
            // Load the script
            await new Promise<void>((resolve, reject) => {
              scriptElement = document.createElement("script")
              scriptElement.type = "module"
              scriptElement.src = scriptUrl
              scriptElement.async = true
              scriptElement.onload = () => resolve()
              scriptElement.onerror = () =>
                reject(new Error(`Failed to load script from ${jsSourcePath}`))
              document.head.appendChild(scriptElement)
            })

            // Run the module
            const result = await loadAndRunModule({
              componentName,
              moduleUrl: scriptUrl,
              componentId,
              parentElement: parentRef.current!,
              data: parsedData,
              componentIdForWidgetMgr: id,
              widgetMgr,
            })

            cleanup = result.cleanup
          } catch (error) {
            throw normalizeError(
              error,
              `Failed to load or execute script from ${jsSourcePath}`
            )
          }
        }
      } catch (error) {
        if (isMounted) {
          handleError(error, setError)
        }
      }
    }

    run()

    // Cleanup function
    return () => {
      isMounted = false

      if (cleanup) {
        try {
          cleanup()
        } catch (error) {
          LOG.error(`Failed to run cleanup for element ${id}`, error)
        }
      }

      if (scriptElement?.parentNode) {
        scriptElement.parentNode.removeChild(scriptElement)
      }
    }
  }, [
    componentId,
    data,
    id,
    jsContent,
    jsSourcePath,
    parentRef,
    setError,
    skip,
    widgetMgr,
  ])
}

interface ComponentBaseProps {
  componentName: string
  id: string
  htmlContent: string | undefined
  cssContent: string | undefined
  cssSourcePath: string | undefined
  jsContent: string | undefined
  jsSourcePath: string | undefined
  data: string | undefined
  widgetMgr: WidgetStateManager
}

const IsolatedComponent: FC<ComponentBaseProps> = ({
  componentName,
  id,
  htmlContent,
  cssContent,
  cssSourcePath,
  jsContent,
  jsSourcePath,
  data,
  widgetMgr,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const shadowRootRef = useRef<ShadowRoot | null>(null)
  const [isShadowRootReady, setIsShadowRootReady] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  // Set up Shadow DOM
  useEffect(() => {
    if (!containerRef.current) return

    try {
      // Don't try to attach a shadow root if the element already has one
      if (containerRef.current.shadowRoot) {
        shadowRootRef.current = containerRef.current.shadowRoot
        setIsShadowRootReady(true)
        return
      }

      shadowRootRef.current = containerRef.current.attachShadow({
        mode: "open",
      })
      setIsShadowRootReady(true)
    } catch (error) {
      handleError(error, setError, "Failed to create shadow DOM")
    }
  }, [id])

  const shouldSkipContent = !isShadowRootReady || !!error

  useHandleHtmlAndCssContent({
    containerRef: shadowRootRef,
    cssContent,
    cssSourcePath,
    html: htmlContent,
    setError,
    skip: shouldSkipContent,
  })

  useHandleJsContent({
    componentName,
    data,
    id,
    jsContent,
    jsSourcePath,
    parentRef: shadowRootRef,
    setError,
    skip: shouldSkipContent,
    widgetMgr,
  })

  if (error) {
    return (
      <ErrorElement
        name="BidiComponent Error"
        message={error.message}
        stack={error.stack}
      />
    )
  }

  return <div ref={containerRef} data-testid="stBidiComponent-isolated" />
}

const NonIsolatedComponent: FC<ComponentBaseProps> = ({
  componentName,
  cssContent,
  cssSourcePath,
  data,
  htmlContent,
  id,
  jsContent,
  jsSourcePath,
  widgetMgr,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<Error | null>(null)

  useHandleHtmlAndCssContent({
    containerRef,
    cssContent,
    cssSourcePath,
    html: htmlContent,
    setError,
    skip: !!error,
  })

  useHandleJsContent({
    componentName,
    data,
    id,
    jsContent,
    jsSourcePath,
    parentRef: containerRef,
    widgetMgr,
    setError,
    skip: !!error,
  })

  if (error) {
    return (
      <ErrorElement
        name="BidiComponent Error"
        message={error.message}
        stack={error.stack}
      />
    )
  }

  return <div ref={containerRef} data-testid="stBidiComponent-regular" />
}

const BidiComponent: FC<BidiComponentProps> = ({ element, widgetMgr }) => {
  const {
    componentName,
    cssContent,
    cssSourcePath,
    data,
    htmlContent,
    id,
    isolateStyles,
    jsContent,
    jsSourcePath,
  } = element

  return isolateStyles ? (
    <IsolatedComponent
      componentName={componentName}
      id={id}
      htmlContent={htmlContent?.trim()}
      cssContent={cssContent?.trim()}
      cssSourcePath={cssSourcePath || undefined}
      jsContent={jsContent || undefined}
      jsSourcePath={jsSourcePath || undefined}
      data={data}
      widgetMgr={widgetMgr}
    />
  ) : (
    <NonIsolatedComponent
      componentName={componentName}
      id={id}
      htmlContent={htmlContent?.trim()}
      cssContent={cssContent?.trim()}
      cssSourcePath={cssSourcePath || undefined}
      jsContent={jsContent || undefined}
      jsSourcePath={jsSourcePath || undefined}
      data={data}
      widgetMgr={widgetMgr}
    />
  )
}

export default memo(BidiComponent)

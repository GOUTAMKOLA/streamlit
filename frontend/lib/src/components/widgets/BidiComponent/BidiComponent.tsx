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

import React, {
  FC,
  memo,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react"

import { getLogger } from "loglevel"

import type { BidiComponent as BidiComponentProto } from "@streamlit/protobuf"

import type { WidgetStateManager } from "~lib/WidgetStateManager"
import ErrorElement from "~lib/components/shared/ErrorElement"
import { useRequiredContext } from "~lib/hooks/useRequiredContext"
import { LibContext } from "~lib/components/core/LibContext"

import { makeTriggerId } from "./idBuilder"
import {
  BidiComponentContext,
  BidiComponentContextShape,
} from "./BidiComponentContext"
import type {
  BidiComponentState,
  ComponentResult,
  StV2ComponentArgs,
} from "./types"

//#region Utility functions
const LOG = getLogger("BidiComponent")

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

const loadAndRunModule = async <T extends BidiComponentState>({
  componentId,
  componentIdForWidgetMgr,
  componentName,
  data,
  fragmentId,
  getWidgetValue,
  moduleUrl,
  parentElement,
  widgetMgr,
}: {
  componentId: string
  componentIdForWidgetMgr: string
  componentName: string
  data: unknown
  getWidgetValue: () => T
  fragmentId: string | undefined
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

  const setStateValue = <T extends BidiComponentState>(
    name: string,
    value: T[keyof T]
  ): void => {
    let newValue: T = {} as T

    try {
      const existingValue = getWidgetValue()

      newValue = { ...existingValue, [name]: value } as T
    } catch (error) {
      LOG.error(`Failed to get existing value for ${name}`, error)
      newValue = { [name]: value } as T
    }

    void widgetMgr.setJsonValue(
      { id: componentIdForWidgetMgr },
      newValue,
      { fromUi: true },
      fragmentId
    )
  }

  const setTriggerValue = <T extends BidiComponentState>(
    name: string,
    value: T[keyof T]
  ): void => {
    const triggerId = makeTriggerId(componentIdForWidgetMgr, name)
    void widgetMgr.setTriggerValue(
      { id: triggerId },
      { fromUi: true },
      fragmentId,
      value
    )
  }

  const cleanup = module.default({
    name: componentName,
    data,
    // NOTE: We are using `stKey` instead of `key` because React gives a warning
    // that it is a reserved prop.
    stKey: componentId,
    parentElement,
    setStateValue,
    setTriggerValue,
  } satisfies StV2ComponentArgs)

  return {
    cleanup: typeof cleanup === "function" ? cleanup : undefined,
  }
}
//#endregion

//#region Hooks
const useHandleHtmlAndCssContent = ({
  containerRef,
  setError,
  skip = false,
}: {
  containerRef: React.RefObject<HTMLElement | ShadowRoot>
  setError: (error: Error) => void
  skip?: boolean
}): React.MutableRefObject<HTMLDivElement | null> => {
  const contentRef = useRef<HTMLDivElement | null>(null)

  const {
    htmlContent: html,
    cssContent,
    cssSourcePath,
    componentName,
  } = useRequiredContext(BidiComponentContext)

  const {
    componentRegistry: { getBidiComponentURL },
  } = useContext(LibContext)

  /**
   * Calculate this in a useMemo to reduce unnecessary re-runs of the useEffect
   */
  const cssLinkHref = useMemo(() => {
    if (!cssSourcePath) {
      return undefined
    }

    return getBidiComponentURL(componentName, cssSourcePath)
  }, [componentName, cssSourcePath, getBidiComponentURL])

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
      } else if (cssLinkHref) {
        const linkElement = document.createElement("link")
        linkElement.href = cssLinkHref
        linkElement.rel = "stylesheet"
        linkElement.onerror = () => {
          handleError(`Failed to load CSS from ${cssLinkHref}`, setError)
        }
        contentRef.current.appendChild(linkElement)
      }

      parent.appendChild(contentRef.current)
    } catch (error) {
      handleError(error, setError, "Failed to process HTML/CSS content")
    }
  }, [html, cssContent, containerRef, cssLinkHref, setError, skip])

  return contentRef
}

const useHandleJsContent = ({
  containerRef,
  setError,
  skip = false,
}: {
  containerRef: React.RefObject<HTMLElement | ShadowRoot>
  setError: (error: Error) => void
  skip?: boolean
}): void => {
  const componentId = `st-bidi-component-${useId()}`

  const {
    componentName,
    data,
    fragmentId,
    getWidgetValue,
    id,
    jsContent,
    jsSourcePath,
    widgetMgr,
  } = useRequiredContext(BidiComponentContext)

  const {
    componentRegistry: { getBidiComponentURL },
  } = useContext(LibContext)

  const jsSourcePathUrl = useMemo(() => {
    if (!jsSourcePath) {
      return undefined
    }
    return getBidiComponentURL(componentName, jsSourcePath)
  }, [componentName, jsSourcePath, getBidiComponentURL])

  useEffect(() => {
    const { current: containerRefCurrent } = containerRef

    if (
      // Skip if the hook is explicitly skipped
      skip ||
      // Skip if there is no JS content or source path
      (!jsContent && !jsSourcePathUrl) ||
      // Skip if the container ref is not available
      !containerRefCurrent
    ) {
      return
    }

    let isMounted = true
    let cleanup: ComponentResult["cleanup"]
    let scriptElement: HTMLScriptElement | undefined

    const run = async (): Promise<void> => {
      try {
        // Handle inline JS content
        if (jsContent) {
          const dataUri = `data:text/javascript;charset=utf-8,${encodeURIComponent(
            jsContent
          )}`

          const result = await loadAndRunModule({
            componentId,
            componentIdForWidgetMgr: id,
            componentName,
            data,
            fragmentId,
            getWidgetValue,
            moduleUrl: dataUri,
            parentElement: containerRefCurrent,
            widgetMgr,
          })

          cleanup = result.cleanup
        }
        // Handle external JS file
        else if (jsSourcePathUrl) {
          const scriptUrl = jsSourcePathUrl

          try {
            // Load the script
            await new Promise<void>((resolve, reject) => {
              scriptElement = document.createElement("script")
              scriptElement.type = "module"
              scriptElement.src = scriptUrl
              scriptElement.async = true
              scriptElement.onload = () => resolve()
              scriptElement.onerror = () =>
                reject(
                  new Error(`Failed to load script from ${jsSourcePathUrl}`)
                )
              document.head.appendChild(scriptElement)
            })

            // Run the module
            const result = await loadAndRunModule({
              componentId,
              componentIdForWidgetMgr: id,
              componentName,
              data,
              fragmentId,
              getWidgetValue,
              moduleUrl: scriptUrl,
              parentElement: containerRefCurrent,
              widgetMgr,
            })

            cleanup = result.cleanup
          } catch (error) {
            throw normalizeError(
              error,
              `Failed to load or execute script from ${jsSourcePathUrl}`
            )
          }
        }
      } catch (error) {
        if (isMounted) {
          handleError(error, setError)
        }
      }
    }

    void run()

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
    componentName,
    containerRef,
    data,
    fragmentId,
    getWidgetValue,
    id,
    jsContent,
    jsSourcePathUrl,
    setError,
    skip,
    widgetMgr,
  ])
}
//#endregion

//#region Internal components
const IsolatedComponent: FC = () => {
  const containerRef = useRef<HTMLDivElement>(null)
  const shadowRootRef = useRef<ShadowRoot | null>(null)
  const [isShadowRootReady, setIsShadowRootReady] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const { id } = useRequiredContext(BidiComponentContext)

  // Set up Shadow DOM
  useEffect(() => {
    if (!containerRef.current) {
      return
    }

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
    } catch (err) {
      handleError(err, setError, "Failed to create shadow DOM")
    }
  }, [id])

  const skip = !isShadowRootReady || !!error

  useHandleHtmlAndCssContent({ containerRef: shadowRootRef, setError, skip })
  useHandleJsContent({ containerRef: shadowRootRef, setError, skip })

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

const NonIsolatedComponent: FC = () => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<Error | null>(null)

  const skip = !!error

  useHandleHtmlAndCssContent({ containerRef, setError, skip })
  useHandleJsContent({ containerRef, setError, skip })

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
//#endregion

type BidiComponentProps = {
  element: BidiComponentProto
  widgetMgr: WidgetStateManager
  fragmentId: string | undefined
}

const BidiComponent: FC<BidiComponentProps> = ({
  element,
  widgetMgr,
  fragmentId,
}) => {
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

  const getWidgetValue = useCallback(() => {
    const value = widgetMgr.getJsonValue(element)
    return value ? JSON.parse(value) : {}
  }, [element, widgetMgr])

  const contextValue = useMemo<BidiComponentContextShape>(() => {
    return {
      componentName,
      cssContent: cssContent?.trim(),
      cssSourcePath: cssSourcePath || undefined,
      data: data ? JSON.parse(data) : undefined,
      fragmentId,
      getWidgetValue,
      htmlContent: htmlContent?.trim(),
      id,
      jsContent: jsContent || undefined,
      jsSourcePath: jsSourcePath || undefined,
      widgetMgr,
    }
  }, [
    componentName,
    cssContent,
    cssSourcePath,
    data,
    fragmentId,
    getWidgetValue,
    htmlContent,
    id,
    jsContent,
    jsSourcePath,
    widgetMgr,
  ])

  return (
    <BidiComponentContext.Provider value={contextValue}>
      {isolateStyles ? <IsolatedComponent /> : <NonIsolatedComponent />}
    </BidiComponentContext.Provider>
  )
}

export default memo(BidiComponent)

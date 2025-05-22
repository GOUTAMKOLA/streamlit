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
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react"

import capitalize from "lodash/capitalize"
import { getLogger } from "loglevel"

import type { BidiComponent as BidiComponentProto } from "@streamlit/protobuf"

import type { WidgetStateManager } from "~lib/WidgetStateManager"
import ErrorElement from "~lib/components/shared/ErrorElement"
import { useRequiredContext } from "~lib/hooks/useRequiredContext"
import { LibContext } from "~lib/components/core/LibContext"

import {
  BidiComponentContext,
  BidiComponentContextShape,
} from "./BidiComponentContext"
import type {
  ComponentResult,
  OnHandlerKey,
  OnHandlers,
  StBidiComponentV2Args,
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

const loadAndRunModule = async ({
  componentId,
  componentIdForWidgetMgr,
  componentName,
  data,
  fragmentId,
  moduleUrl,
  parentElement,
  registeredHandlerNames,
  widgetMgr,
}: {
  componentId: string
  componentIdForWidgetMgr: string
  componentName: string
  data: unknown
  fragmentId: string | undefined
  moduleUrl: string
  parentElement: HTMLElement | ShadowRoot
  registeredHandlerNames: string[]
  widgetMgr: WidgetStateManager
}): Promise<ComponentResult> => {
  const module = await import(/* @vite-ignore */ moduleUrl)

  if (!module) {
    throw new Error("JS module does not exist.")
  }

  if (!module.default || typeof module.default !== "function") {
    throw new Error("JS module does not have a default export function.")
  }

  const handlers = registeredHandlerNames.reduce<OnHandlers>((acc, name) => {
    const handlerName = `on${capitalize(name)}` as OnHandlerKey

    acc[handlerName] = (value?: unknown) => {
      // eslint-disable-next-line testing-library/no-debugging-utils
      LOG.debug(`BidiComponent: ${handlerName} called with value`, value)

      if (handlerName === "onClick") {
        void widgetMgr.setTriggerValue(
          { id: componentIdForWidgetMgr },
          { fromUi: true },
          fragmentId
        )
        return
      }

      void widgetMgr.setJsonValue(
        { id: componentIdForWidgetMgr },
        value,
        { fromUi: true },
        fragmentId
      )
    }

    return acc
  }, {})

  const cleanup = module.default({
    name: componentName,
    data,
    // NOTE: We are using `stKey` instead of `key` because React gives a warning
    // that it is a reserved prop.
    stKey: componentId,
    parentElement,
    // TODO: FIXME:
    childContainerIDs: [],
    ...handlers,
  } satisfies StBidiComponentV2Args)

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
    id,
    jsContent,
    jsSourcePath,
    registeredHandlerNames,
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
    if (
      // Skip if the hook is explicitly skipped
      skip ||
      // Skip if there is no JS content or source path
      (!jsContent && !jsSourcePathUrl) ||
      // Skip if the container ref is not available
      !containerRef.current
    ) {
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
            parentElement: containerRef.current!,
            data: parsedData,
            componentIdForWidgetMgr: id,
            fragmentId,
            registeredHandlerNames,
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
              componentName,
              moduleUrl: scriptUrl,
              componentId,
              parentElement: containerRef.current!,
              data: parsedData,
              componentIdForWidgetMgr: id,
              fragmentId,
              registeredHandlerNames,
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
    id,
    jsContent,
    jsSourcePathUrl,
    registeredHandlerNames,
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
    registeredHandlerNames,
  } = element

  const contextValue = useMemo<BidiComponentContextShape>(() => {
    return {
      componentName,
      cssContent: cssContent?.trim(),
      cssSourcePath: cssSourcePath || undefined,
      data: data || undefined,
      fragmentId,
      htmlContent: htmlContent?.trim(),
      id,
      jsContent: jsContent || undefined,
      jsSourcePath: jsSourcePath || undefined,
      registeredHandlerNames,
      widgetMgr,
    }
  }, [
    componentName,
    cssContent,
    cssSourcePath,
    data,
    fragmentId,
    htmlContent,
    id,
    jsContent,
    jsSourcePath,
    registeredHandlerNames,
    widgetMgr,
  ])

  return (
    <BidiComponentContext.Provider value={contextValue}>
      {isolateStyles ? <IsolatedComponent /> : <NonIsolatedComponent />}
    </BidiComponentContext.Provider>
  )
}

export default memo(BidiComponent)

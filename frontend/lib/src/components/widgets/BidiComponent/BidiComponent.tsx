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

import React, { FC, memo, useEffect, useId, useRef } from "react"

import { getLogger } from "loglevel"

import { BidiComponent as BidiComponentProto } from "@streamlit/protobuf"

const LOG = getLogger("BidiComponent")

export type BidiComponentProps = {
  element: BidiComponentProto
}

const BidiComponent: FC<BidiComponentProps> = ({ element }) => {
  const { id, jsContent } = element

  const componentId = useId()

  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!jsContent) {
      LOG.error("BidiComponent Error: No JavaScript content provided.")
      return
    }

    if (!containerRef.current) {
      LOG.error("BidiComponent Error: No container element provided.")
      return
    }

    // Construct a data URI for the JavaScript content
    const dataUri = `data:text/javascript;charset=utf-8,${encodeURIComponent(
      jsContent
    )}`
    const containerElement = containerRef.current

    const handleImport = async (): Promise<void> => {
      try {
        // Dynamically import the module from the data URI
        const module = await import(/* @vite-ignore */ dataUri)
        if (module.default && typeof module.default === "function") {
          // Call the default exported function, passing the container element
          module.default({
            // TODO: Add a name
            name: "",
            // TODO: Add data
            data: null,
            key: componentId,
            parentElement: containerElement,
            // TODO: Add child container IDs
            childContainerIDs: [],
          })
        } else {
          LOG.error(
            "BidiComponent Error: Module does not have a default export function.",
            id
          )
        }
      } catch (error) {
        LOG.error(
          `BidiComponent Error: Failed to load or execute script for element ${id}`,
          error
        )
      }
    }

    handleImport()

    return () => {
      if (containerElement) {
        containerElement.innerHTML = ""
      }
    }
    // NOTE: Intentionally only running on mount in order to achieve the product behavior of
    // not allowing `jsContent` to be updated after the component is mounted.
    // eslint-disable-next-line react-compiler/react-compiler
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div ref={containerRef} data-testid={`stBidiComponent-${element.id}`} />
  )
}

export default memo(BidiComponent)

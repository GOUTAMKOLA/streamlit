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

import { CSSProperties, FC, PropsWithChildren, useMemo } from "react"

import isObject from "lodash/isObject"
import kebabCase from "lodash/kebabCase"

import { useEmotionTheme } from "~lib/hooks/useEmotionTheme"

/**
 * Recursively converts a nested object to CSS custom properties
 * with the --st- prefix and kebab-case naming
 */
const objectToCssCustomProperties = (
  obj: Record<string, unknown>,
  prefix = "--st"
): CSSProperties => {
  const result: Record<string, string> = {}

  const traverse = (
    current: Record<string, unknown>,
    currentPrefix: string
  ): void => {
    Object.entries(current).forEach(([key, value]) => {
      const kebabKey = kebabCase(key)
      const propertyName = `${currentPrefix}-${kebabKey}`

      if (isObject(value)) {
        // Recursively traverse nested objects
        traverse(value as Record<string, unknown>, propertyName)
      } else {
        // Convert the value to string for CSS custom properties
        result[propertyName] = String(value)
      }
    })
  }

  traverse(obj, prefix)
  return result as CSSProperties
}

/**
 * ThemeCssProvider is a component that provides the current Emotion theme as
 * CSS custom properties by applying them to a wrapping element.
 */
export const ThemeCssProvider: FC<PropsWithChildren> = ({ children }) => {
  const theme = useEmotionTheme()

  const styles = useMemo(() => {
    return objectToCssCustomProperties(theme)
  }, [theme])

  return <div style={styles}>{children}</div>
}

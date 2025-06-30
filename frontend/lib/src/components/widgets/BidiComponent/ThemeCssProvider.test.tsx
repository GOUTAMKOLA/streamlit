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

import { describe, expect, it } from "vitest"
import { render } from "@testing-library/react"

import {
  objectToCssCustomProperties,
  ThemeCssProvider,
} from "./ThemeCssProvider"

describe("objectToCssCustomProperties", () => {
  it("should convert flat object to CSS custom properties", () => {
    const input = {
      primary: "#ff0000",
      secondary: "#00ff00",
      inSidebar: false,
      fontSize: 16,
    }

    const result = objectToCssCustomProperties(input)

    expect(result).toEqual({
      "--st-primary": "#ff0000",
      "--st-secondary": "#00ff00",
      "--st-in-sidebar": "false",
      "--st-font-size": "16",
    })
  })

  it("should convert nested object to CSS custom properties with proper kebab-case naming", () => {
    const input = {
      colors: {
        primary: "#ff0000",
        secondary: "#00ff00",
        bgColor: "#ffffff",
        bodyText: "#000000",
      },
      fontSizes: {
        sm: "0.875rem",
        md: "1rem",
        lg: "1.25rem",
        baseFontSize: 16,
      },
      spacing: {
        sm: "0.5rem",
        md: "0.75rem",
        lg: "1rem",
      },
    }

    const result = objectToCssCustomProperties(input)

    expect(result).toEqual({
      // colors
      "--st-colors-primary": "#ff0000",
      "--st-colors-secondary": "#00ff00",
      "--st-colors-bg-color": "#ffffff",
      "--st-colors-body-text": "#000000",
      // fontSizes
      "--st-font-sizes-sm": "0.875rem",
      "--st-font-sizes-md": "1rem",
      "--st-font-sizes-lg": "1.25rem",
      "--st-font-sizes-base-font-size": "16",
      // spacing
      "--st-spacing-sm": "0.5rem",
      "--st-spacing-md": "0.75rem",
      "--st-spacing-lg": "1rem",
    })
  })

  it("should handle deeply nested objects", () => {
    const input = {
      theme: {
        colors: {
          palette: {
            primary: "#ff0000",
          },
        },
      },
    }

    const result = objectToCssCustomProperties(input)

    expect(result).toEqual({
      "--st-theme-colors-palette-primary": "#ff0000",
    })
  })

  it("should convert boolean and number values to strings", () => {
    const input = {
      isEnabled: true,
      isDisabled: false,
      count: 42,
      ratio: 1.5,
    }

    const result = objectToCssCustomProperties(input)

    expect(result).toEqual({
      "--st-is-enabled": "true",
      "--st-is-disabled": "false",
      "--st-count": "42",
      "--st-ratio": "1.5",
    })
  })

  it("should use custom prefix when provided", () => {
    const input = {
      primary: "#ff0000",
      secondary: "#00ff00",
    }

    const result = objectToCssCustomProperties(input, "--custom")

    expect(result).toEqual({
      "--custom-primary": "#ff0000",
      "--custom-secondary": "#00ff00",
    })
  })
})

describe("ThemeCssProvider", () => {
  it("should render children correctly", () => {
    const { getByTestId } = render(
      <ThemeCssProvider>
        <div data-testid="child">Child content</div>
      </ThemeCssProvider>
    )

    expect(getByTestId("child")).toHaveTextContent("Child content")
  })
})

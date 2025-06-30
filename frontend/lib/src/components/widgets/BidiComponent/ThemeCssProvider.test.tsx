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

import { render } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { ThemeCssProvider } from "./ThemeCssProvider"

// Mock the useEmotionTheme hook
vi.mock("~lib/hooks/useEmotionTheme", () => ({
  useEmotionTheme: vi.fn(() => ({
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
    inSidebar: false,
    showSidebarBorder: true,
  })),
}))

describe("ThemeCssProvider", () => {
  it("should generate CSS custom properties from theme object", () => {
    const { container } = render(
      <ThemeCssProvider>
        <div data-testid="child">Child content</div>
      </ThemeCssProvider>
    )

    const providerElement = container.firstChild as HTMLElement
    const styles = providerElement.style

    // Test nested object conversion (colors)
    expect(styles.getPropertyValue("--st-colors-primary")).toBe("#ff0000")
    expect(styles.getPropertyValue("--st-colors-secondary")).toBe("#00ff00")
    expect(styles.getPropertyValue("--st-colors-bg-color")).toBe("#ffffff")
    expect(styles.getPropertyValue("--st-colors-body-text")).toBe("#000000")

    // Test nested object conversion (fontSizes with camelCase)
    expect(styles.getPropertyValue("--st-font-sizes-sm")).toBe("0.875rem")
    expect(styles.getPropertyValue("--st-font-sizes-md")).toBe("1rem")
    expect(styles.getPropertyValue("--st-font-sizes-lg")).toBe("1.25rem")
    expect(styles.getPropertyValue("--st-font-sizes-base-font-size")).toBe(
      "16"
    )

    // Test nested object conversion (spacing)
    expect(styles.getPropertyValue("--st-spacing-sm")).toBe("0.5rem")
    expect(styles.getPropertyValue("--st-spacing-md")).toBe("0.75rem")
    expect(styles.getPropertyValue("--st-spacing-lg")).toBe("1rem")

    // Test boolean conversion
    expect(styles.getPropertyValue("--st-in-sidebar")).toBe("false")
    expect(styles.getPropertyValue("--st-show-sidebar-border")).toBe("true")
  })

  it("should render children correctly", () => {
    const { getByTestId } = render(
      <ThemeCssProvider>
        <div data-testid="child">Child content</div>
      </ThemeCssProvider>
    )

    expect(getByTestId("child")).toHaveTextContent("Child content")
  })
})

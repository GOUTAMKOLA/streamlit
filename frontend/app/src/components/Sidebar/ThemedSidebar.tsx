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

import React, { ReactElement, useContext } from "react"

import { getLuminance } from "color2k"

import {
  createTheme,
  LibContext,
  ThemeConfig,
  ThemeProvider,
} from "@streamlit/lib"
import { notNullOrUndefined } from "@streamlit/utils"
import { CustomThemeConfig } from "@streamlit/protobuf"

import Sidebar, { SidebarProps } from "./Sidebar"

const getH1FontSize = (
  themeConfig: Partial<CustomThemeConfig> = {},
  baseFontSize: number = 16
): string => {
  // Header font size set in the following priority:
  // 1. If theme.sidebar.h1FontSize is set, use it
  // 2. If theme.h1FontSize is set, use a scaled down version of it for sidebar
  // 3. If neither set, use the default sidebar h1FontSize (1.5rem)
  if (themeConfig.sidebar?.h1FontSize) {
    return themeConfig.sidebar.h1FontSize
  } else if (themeConfig.h1FontSize) {
    // Scale down the h1FontSize for sidebar by 45%
    if (themeConfig.h1FontSize.endsWith("px")) {
      // Handle px case:
      const remValue = (parseInt(themeConfig.h1FontSize) / baseFontSize) * 0.55
      const roundedRemValue = Math.round(remValue * 8) / 8 // Round to nearest 8th
      return `${roundedRemValue}rem`
    } else if (themeConfig.h1FontSize.endsWith("rem")) {
      // Handle rem case:
      const remValue = parseFloat(themeConfig.h1FontSize) * 0.55
      const roundedRemValue = Math.round(remValue * 8) / 8 // Round to nearest 8th
      return `${roundedRemValue}rem`
    }
  }

  return "1.5rem"
}

export const createSidebarTheme = (theme: ThemeConfig): ThemeConfig => {
  let sidebarOverride = {}
  if (notNullOrUndefined(theme.themeInput?.sidebar)) {
    sidebarOverride = theme.themeInput.sidebar
  }

  // Either use the configured background color or secondary background from main theme:
  const sidebarBackground =
    theme.themeInput?.sidebar?.backgroundColor ||
    theme.emotion.colors.secondaryBg

  // Either use the configured secondary background color or background from main theme:
  const secondaryBackgroundColor =
    theme.themeInput?.sidebar?.secondaryBackgroundColor ||
    theme.emotion.colors.bgColor

  // TESTING:
  const h1FontSize = getH1FontSize(theme.themeInput)

  // Override the background and secondary background colors in sidebar overwrites:
  sidebarOverride = {
    ...sidebarOverride,
    backgroundColor: sidebarBackground,
    secondaryBackgroundColor: secondaryBackgroundColor,
    h1FontSize,
  }

  const baseTheme =
    getLuminance(sidebarBackground) > 0.5
      ? CustomThemeConfig.BaseTheme.LIGHT
      : CustomThemeConfig.BaseTheme.DARK

  return createTheme(
    "Sidebar",
    {
      ...theme.themeInput, // Use the theme props from the main theme as basis
      base: baseTheme,
      ...sidebarOverride,
    },
    undefined, // Creating a new theme from scratch
    true // inSidebar
  )
}

const ThemedSidebar = ({
  children,
  ...sidebarProps
}: Omit<SidebarProps, "chevronDownshift">): ReactElement => {
  const { activeTheme } = useContext(LibContext)
  const sidebarTheme = createSidebarTheme(activeTheme)

  return (
    <ThemeProvider
      theme={sidebarTheme.emotion}
      baseuiTheme={sidebarTheme.basewebTheme}
    >
      <Sidebar {...sidebarProps}>{children}</Sidebar>
    </ThemeProvider>
  )
}

export default ThemedSidebar

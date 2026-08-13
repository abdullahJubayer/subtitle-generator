---
name: ui-design
description: Standardized UI/UX design system and QSS styling guidelines for building premium, modern Desktop GUI components. Use when designing, styling, or refactoring user interfaces.
---

# Modern Desktop GUI Design System & UX Standards

## 1. Core Visual Principles
- **Function-Driven Design:** Clear visual hierarchy, frictionless interactions, fast feedback.
- **No Emojis in UI:** Strictly DO NOT use emojis in UI labels, buttons, tab titles, window titles, headers, dialogs, or status indicators. Use clean text labels, professional typography, or vector SVG icons instead.
- **Premium Dark Palette (Catppuccin Macchiato Aesthetic):**
  - Window Background: `#1e1e2e` (Deep Base)
  - Card / Panel Surface: `#181825` (Elevated Container)
  - Input / Control Surface: `#313244` (Surface Layer)
  - Primary Accent: `#89b4fa` (Accent Blue)
  - Secondary Accent: `#b4befe` (Lavender)
  - Success Accent: `#a6e3a1` (Soft Green)
  - Warning Accent: `#f9e2af` (Warm Amber)
  - Error / Critical Accent: `#f38ba8` (Soft Red)
  - Main Text: `#cdd6f4` (High Contrast Text)
  - Muted Text: `#a6adc8` (Subtext / Labels)

---

## 2. Typographic Hierarchy
- **Header Typeface:** Bold 16px - 20px with accent color tracking.
- **Body & Controls:** 13px - 14px crisp legible modern sans-serif.
- **Console / Monospace Editors:** 12px `JetBrains Mono` / `Fira Code` / `Menlo` / `Consolas` with 1.4 line-height.

---

## 3. QSS Styling Rules & Component Design

### Cards & Panels (`QGroupBox`, `QFrame`)
```css
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 14px;
    background-color: #181825;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #89b4fa;
}
```

### Buttons (`QPushButton`)
```css
QPushButton {
    background-color: #89b4fa;
    color: #11111b;
    font-weight: bold;
    border-radius: 6px;
    padding: 8px 16px;
    border: none;
}
QPushButton:hover {
    background-color: #b4befe;
}
QPushButton:pressed {
    background-color: #74c7ec;
}
QPushButton:disabled {
    background-color: #45475a;
    color: #a6adc8;
}
```

### Input Controls (`QLineEdit`, `QComboBox`, `QTextEdit`)
```css
QLineEdit, QComboBox, QTextEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #cdd6f4;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #89b4fa;
}
```

### Tabs (`QTabWidget`, `QTabBar`)
```css
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background-color: #313244;
    color: #89b4fa;
    font-weight: bold;
}
```

---

## 4. Micro-Interactions & Responsiveness
1. **Dynamic Layout Math:** Avoid rigid pixel heights; use fluid layouts (`QVBoxLayout`, `QHBoxLayout`, `QSplitter`) with proper `stretch` factors.
2. **Interactive States:** Every interactive element must provide distinct visual feedback for `hover`, `active`, `focused`, and `disabled` states.
3. **Clean Professional Labels:** Avoid emoji clutter. Use clear, concise text labels (e.g. `Whisper Log`, `LLM Telemetry`, `SRT Preview`) and color-coded status badges for instant clarity.

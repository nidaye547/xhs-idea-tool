#!/usr/bin/env python3
"""
UI 布局可视化工具 - 生成 ASCII 表示帮助理解 UI 结构
通过解析代码生成控件层级和尺寸的可视化输出
"""
import re
from pathlib import Path


def parse_widget_dimensions(source):
    """解析控件的尺寸设置"""
    dimensions = {}

    # 查找 setMinimumSize
    for match in re.finditer(r'self\.(\w+)\.setMinimumSize\(\s*(\d+)\s*,\s*(\d+)\s*\)', source):
        name, w, h = match.groups()
        dimensions[name] = {'min': (int(w), int(h))}

    # 查找 setMaximumWidth
    for match in re.finditer(r'self\.(\w+)\.setMaximumWidth\(\s*(\d+)\s*\)', source):
        name, w = match.groups()
        if name not in dimensions:
            dimensions[name] = {}
        dimensions[name]['max_width'] = int(w)

    # 查找 setFixedWidth
    for match in re.finditer(r'self\.(\w+)\.setFixedWidth\(\s*(\d+)\s*\)', source):
        name, w = match.groups()
        if name not in dimensions:
            dimensions[name] = {}
        dimensions[name]['fixed_width'] = int(w)

    # 查找 setFixedSize
    for match in re.finditer(r'self\.(\w+)\.setFixedSize\(\s*(\d+)\s*,\s*(\d+)\s*\)', source):
        name, w, h = match.groups()
        dimensions[name] = {'fixed': (int(w), int(h))}

    return dimensions


def parse_layout_margins(source):
    """解析布局边距"""
    margins = {}

    # setContentsMargins(left, top, right, bottom)
    for match in re.finditer(r'setContentsMargins\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', source):
        l, t, r, b = match.groups()
        # 找到这个语句所属的布局变量
        pass  # 需要更复杂的上下文分析

    return margins


def generate_layout_tree(source, widget_name="root"):
    """生成布局树结构"""
    tree = []

    # 查找所有 addWidget 调用
    add_widgets = re.findall(r'\.addWidget\(\s*(?:self\.)?(\w+)\s*[,)]', source)

    # 查找所有 addLayout 调用
    add_layouts = re.findall(r'\.addLayout\(\s*(?:self\.)?(\w+)\s*[,)]', source)

    return {'widgets': add_widgets, 'layouts': add_layouts}


def analyze_spacing_issues(source):
    """分析间距问题"""
    issues = []

    # 检查无间距的QVBoxLayout/QHBoxLayout
    layouts_without_spacing = re.findall(
        r'self\.(\w+)\s*=\s*QVBoxLayout\(\).*?addWidget',
        source, re.DOTALL
    )

    # 检查是否设置了 spacing
    has_spacing = re.findall(r'\.setSpacing\(\s*(\d+)\s*\)', source)

    # 检查 contentsMargins
    margins = re.findall(r'setContentsMargins\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', source)

    # 检查 addStretch 或 addSpacing
    has_stretch = 'addStretch' in source
    has_spacing_call = 'addSpacing' in source

    return {
        'spacing_calls': len(has_spacing),
        'margins': margins,
        'has_stretch': has_stretch,
        'has_spacing_call': has_spacing_call
    }


def analyze_selector_specificity():
    """分析样式选择器优先级"""
    styles_file = Path(__file__).parent / 'gui' / 'styles.py'
    with open(styles_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取所有选择器
    selectors = re.findall(r'([\w:>#.+]+)\s*\{', content)

    # 分类选择器
    universal = []      # QWidget, QLabel 等基础选择器
    pseudo = []        # QPushButton:hover 等伪选择器
    descendant = []    # 包含空格后代的
    child = []         # 使用 > 的
    specific = []      # 更具体的选择器

    for sel in selectors:
        sel = sel.strip()
        if any(x in sel for x in [':hover', ':pressed', ':checked', '::', ':selected', ':disabled']):
            pseudo.append(sel)
        elif '>' in sel:
            child.append(sel)
        elif ' ' in sel:
            descendant.append(sel)
        elif '#' in sel or '.' in sel:
            specific.append(sel)
        else:
            universal.append(sel)

    return {
        'universal': list(set(universal)),
        'pseudo': list(set(pseudo)),
        'descendant': list(set(descendant)),
        'child': list(set(child)),
        'specific': list(set(specific))
    }


def check_inheritable_properties():
    """检查 QSS 继承性问题"""
    # Qt 样式表中，只有特定的属性会继承
    # 常见不继承的属性需要显式设置

    inheritable = [
        'font', 'font-family', 'font-size', 'font-style', 'font-weight',
        'color', 'background-color', 'text-align'
    ]

    non_inheritable = [
        'border', 'padding', 'margin', 'min-width', 'max-width',
        'min-height', 'max-height', 'width', 'height',
        'border-radius', 'border-color', 'border-width'
    ]

    return {'inheritable': inheritable, 'non_inheritable': non_inheritable}


def analyze_widget_style_coverage():
    """分析每个控件是否覆盖了所有必要的样式状态"""
    styles_file = Path(__file__).parent / 'gui' / 'styles.py'
    with open(styles_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 控件需要的样式状态
    required_states = {
        'QPushButton': ['normal', 'hover', 'pressed', 'disabled'],
        'QLineEdit': ['normal', 'focus'],
        'QTextEdit': ['normal', 'focus'],
        'QCheckBox': ['normal', 'hover', 'checked'],
        'QTableWidget': ['normal', 'item'],
    }

    coverage = {}

    for widget, states in required_states.items():
        coverage[widget] = {'covered': [], 'missing': []}

        for state in states:
            # 检查是否有对应的样式
            if state == 'normal':
                # 检查有没有这个控件的基础样式
                if f'{widget} {{' in content:
                    coverage[widget]['covered'].append(state)
            else:
                # 检查伪选择器
                if f'{widget}:{state}' in content or f'{widget}::{state}' in content:
                    coverage[widget]['covered'].append(state)
                else:
                    coverage[widget]['missing'].append(state)

    return coverage


def generate_visual_layout_report():
    """生成可视化布局报告"""
    files = {
        'main_window': Path(__file__).parent / 'gui' / 'main_window.py',
        'search_page': Path(__file__).parent / 'gui' / 'search_page.py',
        'favorites_page': Path(__file__).parent / 'gui' / 'favorites_page.py',
        'settings_page': Path(__file__).parent / 'gui' / 'settings_page.py',
    }

    print("=" * 70)
    print("🎨 UI 布局可视化分析")
    print("=" * 70)

    for name, filepath in files.items():
        if not filepath.exists():
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        print(f"\n📁 {name}")
        print("-" * 50)

        # 提取控件定义
        widgets = re.findall(r'self\.(\w+)\s*=\s*(Q\w+)\(\)', source)
        print(f"  控件数量: {len(widgets)}")

        # 控件类型分布
        widget_types = {}
        for name_, wtype in widgets:
            widget_types[wtype] = widget_types.get(wtype, 0) + 1

        print(f"  控件类型分布:")
        for wtype, count in sorted(widget_types.items(), key=lambda x: -x[1]):
            print(f"    • {wtype}: {count}")

        # 分析间距
        spacing = analyze_spacing_issues(source)
        print(f"\n  间距设置:")
        print(f"    • setSpacing 调用: {spacing['spacing_calls']} 次")
        print(f"    • setContentsMargins 调用: {len(spacing['margins'])} 次")
        print(f"    • addStretch: {'是' if spacing['has_stretch'] else '否'}")
        print(f"    • addSpacing: {'是' if spacing['has_spacing_call'] else '否'}")

        # 尺寸设置
        dimensions = parse_widget_dimensions(source)
        if dimensions:
            print(f"\n  尺寸设置:")
            for name_, dim in list(dimensions.items())[:5]:  # 只显示前5个
                print(f"    • {name_}: {dim}")

    print("\n" + "=" * 70)
    print("📊 样式选择器分析")
    print("=" * 70)

    selectors = analyze_selector_specificity()
    print(f"\n  基础选择器 ({len(selectors['universal'])}): {selectors['universal'][:5]}")
    print(f"  伪选择器 ({len(selectors['pseudo'])}): {selectors['pseudo'][:5]}")
    print(f"  后代选择器 ({len(selectors['descendant'])}): {selectors['descendant'][:3]}")
    print(f"  子选择器 ({len(selectors['child'])}): {selectors['child'][:3]}")

    print("\n" + "=" * 70)
    print("✅ 样式状态覆盖检查")
    print("=" * 70)

    coverage = analyze_widget_style_coverage()
    for widget, result in coverage.items():
        status = "完整" if not result['missing'] else f"缺少: {result['missing']}"
        print(f"  {widget}: {status}")


def check_common_style_mistakes():
    """检查常见的样式错误"""
    styles_file = Path(__file__).parent / 'gui' / 'styles.py'
    settings_file = Path(__file__).parent / 'gui' / 'settings_page.py'

    issues = []

    with open(styles_file, 'r', encoding='utf-8') as f:
        styles_content = f.read()

    with open(settings_file, 'r', encoding='utf-8') as f:
        settings_content = f.read()

    # 问题1: QWidget 设置了宽高属性但期望子控件继承
    if 'QWidget {' in styles_content:
        widget_css = re.search(r'QWidget\s*\{([^}]+)\}', styles_content)
        if widget_css:
            css_text = widget_css.group(1)
            if any(x in css_text for x in ['width', 'height', 'min-width', 'max-width', 'border']):
                issues.append("❌ QWidget 设置了尺寸/border 属性，但 QSS 中 QWidget 宽高通常由布局决定，不应在此设置")

    # 问题2: 没有为 QFormLayout 设置 labelAlignment
    if 'QFormLayout' in settings_content:
        if 'setLabelAlignment' not in settings_content and 'labelAlignment' not in styles_content:
            issues.append("❌ QFormLayout 可能没有设置标签对齐方式，导致标签文字显示异常")

    # 问题3: 交互控件缺少 hover/pressed 状态
    for widget in ['QPushButton', 'QLineEdit', 'QTextEdit']:
        if f'{widget} {{' in styles_content:
            if f'{widget}:hover' not in styles_content and widget in ['QPushButton']:
                issues.append(f"⚠️ {widget} 缺少 :hover 状态样式")

    # 问题4: TABLE_STYLESHEET 检查
    if 'TABLE_STYLESHEET' in styles_content:
        table_css = re.search(r'TABLE_STYLESHEET\s*=\s*(?:f)?"""([\s\S]*?)"""', styles_content)
        if table_css:
            css = table_css.group(1)
            if 'QTableCornerButton' not in css:
                issues.append("⚠️ TABLE_STYLESHEET 可能缺少 QTableCornerButton 样式")
            if 'border' not in css:
                issues.append("⚠️ TABLE_STYLESHEET 可能缺少 border 边框设置")

    return issues


def main():
    generate_visual_layout_report()

    print("\n" + "=" * 70)
    print("🔍 常见样式错误检查")
    print("=" * 70)

    issues = check_common_style_mistakes()
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ 未发现常见错误")


if __name__ == '__main__':
    main()

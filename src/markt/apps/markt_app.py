from __future__ import annotations

import streamlit as st
from markt.convert import headings_to_list, list_to_headings


def main():
    st.set_page_config(page_title="markt: 标题 ↔ 列表 互转", page_icon="🪄", layout="wide")
    st.title("markt: 多级标题 ↔ 有序/无序列表 互转")
    st.caption("在左侧粘贴 Markdown，选择转换方向，右侧实时预览与复制。")

    with st.sidebar:
        mode = st.radio("转换方向", ["标题 → 列表", "列表 → 标题"], index=0)
        st.subheader("参数")
        bullet = st.selectbox("无序列表标记", ["- ", "* ", "+ "], index=0)
        use_ordered = st.checkbox("使用有序列表(标题→列表)", value=False)
        ordered_marker = st.selectbox("有序列表编号格式", [".", ")"], index=0)
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            indent = st.number_input("缩进空格", min_value=1, max_value=8, value=2, step=1)
        with col_b:
            h_start = st.number_input("标题起级", min_value=1, max_value=6, value=1, step=1)
        with col_c:
            h_max = st.number_input("标题最大", min_value=1, max_value=6, value=6, step=1)
        st.caption("列表转标题：按缩进/indent 推断层级；标题转列表：按 # 个数映射缩进。")

    col1, col2 = st.columns(2)
    with col1:
        src = st.text_area("源 Markdown", height=420, placeholder="在此粘贴需要转换的 Markdown…")
    with col2:
        if mode == "标题 → 列表":
            dst = headings_to_list(
                src or "",
                bullet=bullet,
                max_heading=h_max,
                indent_size=int(indent),
                ordered=bool(use_ordered),
                ordered_marker=ordered_marker,
            )
        else:
            dst = list_to_headings(src or "", start_level=int(h_start), max_level=int(h_max), indent_size=int(indent))
        st.text_area("转换结果", value=dst, height=420)
        st.download_button("下载结果.md", data=dst.encode("utf-8"), file_name="result.md", mime="text/markdown")


if __name__ == "__main__":
    main()

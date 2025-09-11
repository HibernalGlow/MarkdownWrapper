from __future__ import annotations

import base64
import html
import streamlit as st
from markt.convert import headings_to_list, list_to_headings


def main():
    st.set_page_config(page_title="markt: 标题 ↔ 列表 互转", page_icon="🪄", layout="wide")
    st.title("markt: 多级标题 ↔ 有序/无序列表 互转")
    st.caption("在左侧粘贴 Markdown，选择转换方向，右侧实时预览与复制。")

    with st.sidebar:
        mode = st.radio("转换方向", ["标题 → 列表", "列表 → 标题"], index=0)
        st.subheader("通用参数")
        col_a, col_b = st.columns(2)
        with col_a:
            indent = st.number_input("缩进空格", min_value=1, max_value=8, value=4, step=1)
        with col_b:
            max_list_depth = st.number_input("最大列表层级(0=不限)", min_value=0, max_value=10, value=0, step=1)

        if mode == "标题 → 列表":
            st.subheader("标题 → 列表 参数")
            bullet = st.selectbox("无序列表标记", ["- ", "* ", "+ "], index=0)
            use_ordered = st.checkbox("使用有序列表", value=False)
            ordered_marker = st.selectbox("有序列表编号格式", [".", ")"], index=0)
            h_max = st.number_input("最大标题级别(超出将删除)", min_value=1, max_value=6, value=6, step=1)
            h_start = 1  # 不使用
        else:
            st.subheader("列表 → 标题 参数")
            h_start = st.number_input("顶层映射到标题级别", min_value=1, max_value=6, value=1, step=1)
            h_max = st.number_input("最大标题级别(超出将删除)", min_value=1, max_value=6, value=6, step=1)
            # 为对齐 UI 定义占位变量
            bullet = "- "
            use_ordered = False
            ordered_marker = "."
        st.caption("限制=删除：超过最大标题级别或最大列表层级的行将被丢弃，不进行下调归一。")

    col1, col2 = st.columns(2)
    with col1:
        src = st.text_area("源 Markdown", height=420, placeholder="在此粘贴需要转换的 Markdown…")
    with col2:
                if mode == "标题 → 列表":
                        dst = headings_to_list(
                                src or "",
                                bullet=bullet,
                                max_heading=int(h_max),
                                indent_size=int(indent),
                                ordered=bool(use_ordered),
                                ordered_marker=ordered_marker,
                                max_list_depth=(int(max_list_depth) if int(max_list_depth) > 0 else None),
                        )
                else:
                        dst = list_to_headings(
                                src or "",
                                start_level=int(h_start),
                                max_level=int(h_max),
                                indent_size=int(indent),
                                max_list_depth=(int(max_list_depth) if int(max_list_depth) > 0 else None),
                        )
                st.text_area("转换结果", value=dst, height=420)
                # 复制按钮（使用前端 clipboard API）
                b64 = base64.b64encode(dst.encode("utf-8")).decode("ascii")
                # st.components.v1.html(
                #         f"""
                #         <div>
                #             <button onclick=\"(function(){{
                #                     const txt = atob('{b64}');
                #                     navigator.clipboard.writeText(txt).then(() => {{
                #                         const el = document.getElementById('copy-status');
                #                         if (el) {{ el.textContent = '已复制'; el.style.color = 'green'; }}
                #                     }}).catch(() => {{
                #                         const el = document.getElementById('copy-status');
                #                         if (el) {{ el.textContent = '复制失败'; el.style.color = 'red'; }}
                #                     }});
                #             }})()\">复制到剪贴板</button>
                #             <span id=\"copy-status\" style=\"margin-left:8px;\"></span>
                #         </div>
                #         """,
                #         height=40,
                # )
                
                st.download_button("下载结果.md", data=dst.encode("utf-8"), file_name="result.md", mime="text/markdown")


if __name__ == "__main__":
    main()

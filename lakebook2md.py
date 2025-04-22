import os
import re
import json
import yaml
import tarfile
from bs4 import BeautifulSoup
from pathlib import Path


class LakebookConverter:
    def __init__(self):
        self.input_path = ""
        self.output_base = Path("output")
        self.temp_dir = Path(".laketmp")

    def get_user_input(self):
        """获取用户输入的lakebook文件路径"""
        print("请将.lakeb文件拖入此窗口，或直接输入文件路径：")
        while True:
            path = input("> ").strip('"\' ')  # 去除可能的引号和空格
            if os.path.isfile(path) and path.endswith('.lakeb'):
                self.input_path = Path(path)
                break
            print("❌ 无效路径，请重新输入有效的.lakeb文件路径：")

    def extract_lakebook(self):
        """解压lakebook文件"""
        self.temp_dir.mkdir(exist_ok=True)
        with tarfile.open(self.input_path) as tar:
            tar.extractall(self.temp_dir)

        # 获取解压后的主目录
        for item in self.temp_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                return item
        return None

    def convert_html_to_markdown(self, html_content):
        """将HTML转换为Markdown"""
        soup = BeautifulSoup(html_content, "html.parser")

        # 转换各种HTML标签为Markdown
        for tag in soup.find_all(["p", "br"]):
            tag.insert_after("\n\n")

        for strong in soup.find_all("strong"):
            strong.string = f"**{strong.get_text()}**"

        for em in soup.find_all("em"):
            em.string = f"*{em.get_text()}*"

        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "image")
            img.replace_with(f"![{alt}]({src})")

        for a in soup.find_all("a"):
            href = a.get("href", "")
            text = a.get_text()
            a.replace_with(f"[{text}]({href})")

        # 清理多余空格和换行
        markdown = str(soup)
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        markdown = re.sub(r" {2,}", " ", markdown)
        return markdown.strip()

    def process_doc(self, doc_data, book_dir, output_folder):
        """处理单个文档"""
        title = doc_data.get("title", "未命名文档")
        doc_file = book_dir / f"{doc_data['url']}.json"

        try:
            with open(doc_file, "r", encoding="utf-8") as f:
                content = json.load(f)

            html_content = content["doc"]["body"]
            markdown = self.convert_html_to_markdown(html_content)

            # 创建安全的文件名
            safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
            output_file = output_folder / f"{safe_title}.md"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n{markdown}")

            print(f"✓ 已转换: {title}")
            return True

        except Exception as e:
            print(f"✗ 转换失败 [{title}]: {str(e)}")
            return False

    def process_book(self, book_dir):
        """处理整个lakebook"""
        meta_file = book_dir / "$meta.json"
        if not meta_file.exists():
            print("❌ 找不到元数据文件 $meta.json")
            return False

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        toc = yaml.safe_load(json.loads(meta["meta"])["book"]["tocYml"])

        # 创建输出文件夹 (使用lakebook文件名)
        output_folder = self.output_base / self.input_path.stem
        output_folder.mkdir(parents=True, exist_ok=True)

        print(f"\n正在转换: {self.input_path.name}")
        print(f"输出到: {output_folder}\n")

        success_count = 0
        for item in toc:
            if item["type"] == "DOC":
                if self.process_doc(item, book_dir, output_folder):
                    success_count += 1

        print(f"\n✅ 转换完成! 成功转换 {success_count} 个文档")
        return True

    def clean_up(self):
        """清理临时文件"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def run(self):
        try:
            self.output_base.mkdir(exist_ok=True)
            self.get_user_input()

            book_dir = self.extract_lakebook()
            if book_dir:
                self.process_book(book_dir)

        except Exception as e:
            print(f"❌ 发生错误: {str(e)}")

        finally:
            self.clean_up()


if __name__ == "__main__":
    converter = LakebookConverter()
    converter.run()
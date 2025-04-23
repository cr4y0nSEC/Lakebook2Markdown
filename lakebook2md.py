import os
import re
import json
import yaml
import tarfile
import shutil
from pathlib import Path
from bs4 import BeautifulSoup


class LakebookConverter:
    def __init__(self):
        self.input_path = ""
        self.output_base = Path("output")
        self.temp_dir = Path(".laketmp")
        self.processed_files = set()

    def get_user_input(self):
        """获取用户输入的路径（文件或文件夹）"""
        print("请将.lakebook文件或文件夹拖入此窗口，或直接输入路径：")
        while True:
            path = input("> ").strip('"\' ')
            path_obj = Path(path)

            if path_obj.is_file() and path.endswith('.lakebook'):
                self.input_path = path_obj
                return "file"
            elif path_obj.is_dir():
                self.input_path = path_obj
                return "dir"
            else:
                print("❌ 无效路径，请重新输入有效的.lakebook文件或包含.lakebook文件的文件夹路径：")

    def extract_lakebook(self, lakebook_path):
        """解压单个lakebook文件"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

        self.temp_dir.mkdir(exist_ok=True)
        with tarfile.open(lakebook_path) as tar:
            tar.extractall(self.temp_dir)

        for item in self.temp_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                return item
        return None

    def convert_html_to_markdown(self, html_content):
        """将HTML转换为Markdown"""
        soup = BeautifulSoup(html_content, "html.parser")

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

        markdown = str(soup)
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        markdown = re.sub(r" {2,}", " ", markdown)
        return markdown.strip()

    def process_doc(self, doc_data, book_dir, output_folder):
        """处理单个文档"""
        title = doc_data.get("title", "未命名文档")
        doc_file = book_dir / f"{doc_data['url']}.json"

        doc_id = doc_data.get("uuid", doc_file.name)
        if doc_id in self.processed_files:
            return False
        self.processed_files.add(doc_id)

        try:
            with open(doc_file, "r", encoding="utf-8") as f:
                content = json.load(f)

            html_content = content["doc"]["body"]
            markdown = self.convert_html_to_markdown(html_content)

            safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
            output_file = output_folder / f"{safe_title}.md"

            if output_file.exists():
                output_file.unlink()

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n{markdown}")

            print(f"✓ 已转换: {title}")
            return True

        except Exception as e:
            print(f"✗ 转换失败 [{title}]: {str(e)}")
            return False

    def process_single_lakebook(self, lakebook_path):
        """处理单个lakebook文件"""
        book_dir = self.extract_lakebook(lakebook_path)
        if not book_dir:
            return False

        meta_file = book_dir / "$meta.json"
        if not meta_file.exists():
            print(f"❌ 找不到元数据文件 $meta.json ({lakebook_path.name})")
            return False

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        toc = yaml.safe_load(json.loads(meta["meta"])["book"]["tocYml"])

        output_folder = self.output_base / lakebook_path.stem
        output_folder.mkdir(parents=True, exist_ok=True)

        print(f"\n正在转换: {lakebook_path.name}")
        print(f"输出到: {output_folder}\n")

        success_count = 0
        for item in toc:
            if item["type"] == "DOC":
                if self.process_doc(item, book_dir, output_folder):
                    success_count += 1

        print(f"\n✅ 转换完成! 成功转换 {success_count} 个文档 ({lakebook_path.name})")
        return True

    def process_directory(self):
        """处理目录下的所有lakebook文件"""
        lakebook_files = list(self.input_path.glob("*.lakebook"))
        if not lakebook_files:
            print(f"❌ 文件夹中没有找到.lakebook文件: {self.input_path}")
            return False

        print(f"\n找到 {len(lakebook_files)} 个.lakebook文件:")
        for i, file in enumerate(lakebook_files, 1):
            print(f"{i}. {file.name}")

        total_success = 0
        for lakebook in lakebook_files:
            if self.process_single_lakebook(lakebook):
                total_success += 1

        print(f"\n🎉 全部完成! 成功转换 {total_success}/{len(lakebook_files)} 个.lakebook文件")
        return True

    def clean_up(self):
        """清理临时文件"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run(self):
        try:
            self.output_base.mkdir(exist_ok=True)
            input_type = self.get_user_input()

            if input_type == "file":
                self.process_single_lakebook(self.input_path)
            else:
                self.process_directory()

        except Exception as e:
            print(f"❌ 发生错误: {str(e)}")
        finally:
            self.clean_up()


if __name__ == "__main__":
    converter = LakebookConverter()
    converter.run()
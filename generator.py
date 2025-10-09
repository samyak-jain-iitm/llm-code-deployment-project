import os
from typing import Dict
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
from github_utils import get_repo_files

current_year = datetime.now().year
load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
owner = os.environ.get("GITHUB_OWNER", "student")
USE_OPENAI = bool(OPENAI_API_KEY)

# Minimal MIT LICENSE text template
MIT_LICENSE_TEXT = f"""
MIT License

Copyright (c) {current_year} {owner}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

def generate_project_files(brief: str, attachments: list, checks: list, task: str, repo_name: str, round_num: int) -> Dict[str, str]:
    """
    Returns a dict mapping filepath -> content (text).
    Uses OpenAI API if available, otherwise deterministic templates.
    """
    files = {}
    repo_url = f"https://github.com/{owner}/{repo_name}"

    if USE_OPENAI:
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)

            attachments_text = ""
            if attachments:
                for i, attachment in enumerate(attachments):
                    attachments_text += f"\n\tAttachment {i+1}"
                    for key, value in attachment.items():
                        attachments_text += f"\n \t\t-{key}: {value}"
            
            checks_text = ""
            if checks:
                for check in checks:
                    checks_text += f"\n\t- {check}"

            if round_num == 1:
                prompt = f"""
                <SYSTEM>: You are an expert frontend developer.

                <USER>: Generate a complete website as JSON mapping filenames to contents.
                Do not echo the task description. Create real working code. Do no use placeholders anywhere.

                TASK: {task}
                BRIEF: {brief}
                ATTACHMENTS (if any): {attachments_text}
                Evaluation CHECKS to satisfy (if any): {checks_text}

                Required files:
                1. index.html — a real single-page working website according to the TASK and ATTACHMENTS assigned. Use clean modern HTML5 and CSS.

                2. README.md — A README file for the project you have generated.
                README file instructions:
                ** KEEP THE MAIN HEADING as h1 (#) AND SUBHEADINGS as h2 (##). USE A BREAK STATEMENT < br > AFTER EACH HEADING TO WRITE CONTENT. **
                - A main heading with a meaningful title for the project website.
                - A "📖 Summary" section summarizing the project's purpose from the brief.
                - A "📋 Features" section listing the key features of the website.
                - A "⚙️ Setup" section explaining how to clone and run the project locally. Use {repo_url} as the repo URL.
                - A "▶️ Usage" section describing how to use the website or app.
                - A "📝 Code Explanation" section explaing the code used to make the website or app.
                - A "🛠️ Technologies Used" section listing the main technologies and libraries used.
                - A "📜 License" section stating that it is under the MIT License.

                3. LICENSE — The MIT License text as follows (USE THE EXACT TEXT AS IS):
                {MIT_LICENSE_TEXT}

                ⚠️ IMPORTANT:
                - Return ONLY valid JSON (no markdown formatting).
                - All file contents must be production-ready.
                - The HTML should be styled (inline <style> or CSS in <head>).
                """
            else:
                files = get_repo_files(token=os.environ.get("GITHUB_TOKEN"), repo_name=repo_name, owner=owner)

                prompt = f"""
                <SYSTEM> You are an expert frontend developer. 
                <USER>: You have been provided with the following existing files in the repo:
                Code file (index.html):
                "
                {files.get('index.html', '')}
                "

                readme file (README.md):
                "
                {files.get('README.md', '')}
                "

                you have been given the following brief for changes to be made to the existing code file:

                BRIEF: {brief}
                ATTACHMENTS (if any): {attachments_text}
                Evaluation checks to satisfy with your updates (if any): {checks_text}
                Make the necessary changes to the code file as per the brief provided and update the README.md according to the changes made in the code.
                Required files:
                1. index.html — An updated code file according to the BRIEF provided. Use clean modern HTML5 and CSS.

                2. README.md — An updated README file for the new project. Dont use placeholder in the setup section, use {repo_url} as the repo URL.
                
                3. LICENSE — KEEP THE ORIGINAL LICENSE FILE AS IS, unless instructed otherwise in the brief. Original License text in case it is missing:
                {MIT_LICENSE_TEXT}

                ⚠️ IMPORTANT:
                - Return ONLY valid JSON (no markdown formatting).
                - All file contents must be production-ready.
                - The HTML should be styled (inline <style> or CSS in <head>).
                """

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=2000
            )

            # The assistant's message should be JSON
            message = resp.choices[0].message.content
            files.update(eval(message))  # assuming LLM returns valid JSON object

        except Exception as e:
            print("LLM generation failed:", e)

    # Fallback minimal template if LLM fails
    if not files:
        files['index.html'] = f"<html><body><h1>{task}</h1><pre>{brief}</pre></body></html>"
        files['README.md'] = f"# {task}\n\n{brief}\n"
        files['LICENSE'] = MIT_LICENSE_TEXT

    return files
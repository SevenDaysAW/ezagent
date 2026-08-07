from setuptools import setup, find_packages

setup(
    name="ezagent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "zai-sdk"
    ],

    author="HardyhEll0",
    author_email="2861205314@qq.com",
    description="A Python Module that you can use z.ai LLM API easily.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/SevenDaysAW/ezagent",
)
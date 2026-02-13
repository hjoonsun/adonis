from setuptools import find_packages, setup

setup(
    name="trading-bot-v1",
    version="0.1.0",
    description="api 를 이용한 주식 자동매매 V1.0 초기 세팅",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
)

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Core dependencies
install_requires = [
    "requests>=2.28.0",
    "pyyaml>=6.0",
]

# Development dependencies
dev_requires = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "mypy>=1.0.0",
    "flake8>=6.0.0",
    "types-requests>=2.28.0",
    "types-PyYAML>=6.0.0",
]

setup(
    name="cloudflare-ufw-sync",
    version="0.1.0",
    author="Thomas Vincent",
    author_email="info@thomasvincent.xyz",
    description="Enterprise-grade Cloudflare IP synchronization for UFW",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/thomasvincent/cloudflare-ufw-sync",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Networking :: Firewalls",
        "Topic :: Security",
    ],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require={
        "dev": dev_requires,
    },
    entry_points={
        "console_scripts": [
            "cloudflare-ufw-sync=cloudflare_ufw_sync.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
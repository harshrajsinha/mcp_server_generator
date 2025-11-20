from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

try:
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    requirements = [
        # MCP Core
        "mcp>=0.1.0",
        
        # Database Drivers
        "sqlalchemy>=2.0.0",
        "pymysql>=1.0.0",
        "psycopg2-binary>=2.9.0",
        "cx-Oracle>=8.3.0",
        "pyodbc>=4.0.0",
        "pymongo>=4.0.0",
        
        # Cloud Databases
        "snowflake-connector-python>=3.0.0",
        "google-cloud-bigquery>=3.0.0",
        "redshift-connector>=2.0.0",
        
        # Security
        "cryptography>=41.0.0",
        "python-dotenv>=1.0.0",
        
        # Utilities
        "pandas>=2.0.0",
        "python-dateutil>=2.8.0",
        "pydantic>=2.0.0",
    ]

setup(
    name="scikiq-dbhandler-mcp",
    version="1.0.0",
    author="ScikiQ Team",
    author_email="support@scikiq.com", 
    description="Database Handler MCP Connector for Claude AI - Enterprise Database Operations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/scikiq/scikiq-dbhandler-mcp",
    project_urls={
        "Bug Tracker": "https://github.com/scikiq/scikiq-dbhandler-mcp/issues",
        "Documentation": "https://docs.scikiq.com/dbhandler-mcp", 
        "Source Code": "https://github.com/scikiq/scikiq-dbhandler-mcp",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10", 
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "scikiq-dbhandler-mcp=scikiq_dbutils.mcp_server.main:main",
            "dbhandler-mcp=scikiq_dbutils.mcp_server.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "scikiq_dbutils": [
            "mcp_server/config/*.json", 
            "mcp_server/config/*.yaml",
            "mcp_server/config/*.ini",
            "*.md",
            "*.txt"
        ],
    },
    keywords="claude mcp database sql connector ai assistant enterprise mysql postgresql oracle sqlserver mongodb snowflake bigquery",
    license="MIT",

    package_data={
        'scikiq_dbutils': ['**/*.yaml'],
    },
)

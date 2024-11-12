from setuptools import setup, find_namespace_packages

setup(
    name="solver-util",
    use_scm_version=True,
    setup_requires=['setuptools_scm>6.0,<7'],
    install_requires=[
        'numpy'
    ],
    extras_require={
        'test': ['pytest-asyncio']
    },
    description="Solver Utils Package",
    packages=find_namespace_packages(include=['titan.*', 'tests.*', 'scripts.*']),
    entry_points={
        'console_scripts': [
            'migrate_solution_tree_store=scripts.titan.solver_util.migrate_solution_tree_store:main',
            'index_solution_tree_store=scripts.titan.solver_util.index_solution_tree_store:main'
        ]
    }
)

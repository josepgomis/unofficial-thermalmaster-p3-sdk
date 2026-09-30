# Release checklist

1. Create `josepgomis/unofficial-thermalmaster-p3-sdk` using the account selected by the owner. Set a real maintainer contact in the ROS manifest/setup before a tagged release.
2. Run the complete SDK CI matrix and ROS jobs. Update `docs/validation.md` with actual results and hardware evidence; never change pending entries based only on mocks.
3. Check package-name availability at `https://pypi.org/pypi/unofficial-thermalmaster-p3/json`. A 404 suggests no current project, but does not reserve the name or guarantee registry acceptance. This must be rechecked immediately before publication.
4. Check dependency licenses and build `python -m build`; run `python -m twine check dist/*`. Install the wheel in a clean environment and follow the quick start.
5. Update version consistently in pyproject, SDK __version__, ROS setup/package.xml and changelog. Create tag `v0.1.0` and a GitHub release with wheel and sdist.
6. Configure GitHub environments `testpypi` and `pypi` with appropriate environment protection and a scoped `PYPI_API_TOKEN` secret. Run the manual publication workflow on the release tag, first to TestPyPI, then to PyPI. It never publishes automatically on a push.
7. Verify installation from the registry, then update README's publication status. Never put tokens in code, command output, or issues.

Foxy compatibility limits the SDK to Python 3.8-compatible syntax. Package dependencies resolve versions compatible with the user's Python. Preserve 3.8 in CI when updating dependencies. A pre-1.0 release must disclose unsupported or unverified capabilities.

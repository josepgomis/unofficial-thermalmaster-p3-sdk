# Release checklist

1. The public repository is `josepgomis/unofficial-thermalmaster-p3-sdk`. Maintainer metadata uses `josepgomis` and `josepgomis@users.noreply.github.com`; support goes through Issues.
2. Run the complete SDK CI matrix and ROS jobs. Update `docs/validation.md` with actual results and hardware evidence; never change pending entries based only on mocks.
3. Check package-name availability at `https://pypi.org/pypi/unofficial-thermalmaster-p3/json`. A 404 suggests no current project, but does not reserve the name or guarantee registry acceptance. This must be rechecked immediately before publication.
4. Check dependency licenses and build `python -m build`; run `python -m twine check dist/*`. Install the wheel in a clean environment and follow the quick start.
5. Update version consistently in pyproject, SDK __version__, ROS setup/package.xml and changelog. After physical Windows checks, create tag `v0.1.0` and an alpha GitHub release with wheel, sdist and the actual P3 sample zip below 10 MB. Disclose the owner's interrupted endurance run; do not claim a completed 30-minute test. Pin installation commands to the tag. Gallery frames must be physical acquisitions with recorded provenance.
6. Configure GitHub environments `testpypi` and `pypi` with appropriate environment protection and a scoped `PYPI_API_TOKEN` secret. Run the manual publication workflow on the release tag, first to TestPyPI, then to PyPI. It never publishes automatically on a push.
7. Verify installation from the registry, then update README's publication status. Never put tokens in code, command output, or issues.

Foxy compatibility limits the SDK to Python 3.8-compatible syntax. Package dependencies resolve versions compatible with the user's Python. Preserve 3.8 in CI when updating dependencies. A pre-1.0 release must disclose unsupported or unverified capabilities.

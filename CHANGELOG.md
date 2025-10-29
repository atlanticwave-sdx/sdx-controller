# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - Unreleased

### Added

- TODO

### Fixed

- Fixed MongoDB documents key for historical connection that must be string (#479)
- Fixed nested documents on ports collection (#480)
- Updated to use new Kytos API when placing connection
- Added exception handler to LC message processing

### Changed

- TODO


## [2.0.0] - 2023-05-31

### Added

- Test coverage reporting with coveralls.io (#109)
- Implement BAPM with RabbitMQ (#40)
- Build and publish container images from CI (#124)
- Add code formatting checks on CI (#110)
- Add GitHub Actions for CI (#24, #117, #111)

### Fixed

- Make tests more usable (#94, #133)
- Avoid installing unused packages in bapm-server image (#157)

### Changed

- Use .env file for configuration (#163, #166)
- Update connection handler (#140, #149)
- Return topology correctly (#142)
- Use new pce API (#119)
- Use MongoDB instead of SQLite (#126, #137, #138, #169)
- Dockerfile updates (#121, #112, #148, #166)
- Update pce and datamodel imports (#115)


## [1.0.0] - 2022-06-22

No Changelog entries available.


[2.0.0]: https://github.com/atlanticwave-sdx/sdx-controller/compare/1.0.0...2.0.0
[1.0.0]: https://github.com/atlanticwave-sdx/sdx-controller/compare/d06e415...1.0.0

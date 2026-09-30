# Contributing

Start with the README development commands. Keep USB access, radiometry, recording, viewer and ROS adapters separate. The base SDK must import without OpenCV or ROS.

For USB changes, link protocol evidence and add tests using synthetic packet data. Never commit vendor binaries, private captures, serial numbers, or recordings with identifiable content. Record the OS, architecture, firmware and driver used for physical tests. Hardware claims require actual hardware evidence.

For public API changes, update examples, docs and changelog. v0.x can evolve, but avoid unnecessary breakage and explain migration steps. Run SDK tests and build checks; ROS changes also require tests in the affected distributions.

Open issues with a minimal reproduction and environment details. Pull requests should describe the user-visible change and validation. This is a community project; no response-time guarantee is implied.

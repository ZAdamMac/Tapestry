# Welcome to the Tarnished Tale Contributor Guidelines!
Hey, thanks for checking us out! Tapestry's renaissance phase of development is ambitious at best, which means we're always looking for contributors to come in and help us make a best effort at producing something truly useful - a secure, trust-minimized backup tool made with the modern internet and the user in mind.

First off, let me just say that any contribution matters - from pull-requesting in new functions, to requesting new features, or even just reporting your crashes and bugs. Right now a lot of development is underway. A lot of our framework is super minimal. Tapestry doesn't have automated crash and bug reporting, and its unlikely it ever will. I'm just one guy with a few spare hours in the evening trying to put this thing together. Everything you contribute helps.

Secondly, we do have a few resources for the eager:
- [**Discord Server:**](https://discord.gg/56msGFT) easily the fastest way to join in the conversation or ask a question;
- [Email Development Team](mailto:tapdev@psavlabs.com);
- and, of course, this guide!

# Development Team
While everyone who contributes to the project is part of our development team, the capital-letters Development Team currently consists of github user ZAdamMac.

# Feature Requests
We're always happy to have a look at requests for new features. They further our quest for maximum utility and usability.

## Filing a Feature Request
If you have a feature request for Tapestry, go ahead and open a new issue at this repo. Be sure to head the title of the request with `[RFC]`. The development team will cross-post your request in announcements to the discord and any other contact trains we happen to be using at the time, opening the request up for commentary by other members. **A minimum of 30 days later**, the same group will decide whether or not to include the feature, or some version of it, into the development process. If the feature is complicated or discussion over it is lively, this decision process may be extended as necessary to allow the matter to resolve.

# Bug Reports
We kind of can't overstate the importance of providing your bug reports to us. It's so important we've made a template for them. When Tapestry crashes on your system, we have no idea what happened or why. Please be encouraged to file an issue and fill out the bugs form. Super important stuff.

# Contributing with Code: The Pull Request!
Here at Tapestry we use Fork and Request. If you want to contribute to the development process with your code, the preferred method is to first fork the repo, make your changes there, and then submit a pull request. For obvious reasons all submissions are subject to review. To make this whole process easier, be sure to use nice, clear, descriptive code. Provide documentation or comments as needed.

In general though, we're super happy to have any help that we can. People who contribute with code are being kept track of and will be included in the credits.

## Testing
Tapestry is tested through the use of functional tests - these tests can be found in the testing folder of the main repo, under `functional-tests.py` and the corresponding documentation. Passing the functional tests merely shows your changes aren't breaking to the core behaviour of Tapestry - it will not test the effectiveness of your new features.

If your pull request adds features, be sure to add the corresponding tests to functional-tests.py and submit the new copy with your PR. Also, your PR should include the output of at least one successful test log.

# Contributing with Coins
Lastely, as a hobby project, we're obviously working with the bare minimum funding possible - luckily, this sort of thing also doesn't take much. If you'd like to donate to keep Tapestry's development alive, the current money repo is [ko-fi.com](https://ko-fi.com/PSavLabs). Obviously, if a permanent developer team is adopted, this model will have to change.

At present, we simply have no way for you to contribute with cryptocurrencies. 

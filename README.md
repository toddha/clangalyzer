# Clangalyzer
[maintainer: toddha]

## Overview

The clangalyzer does what it says - it performs analysis of what clang is doing when compiling, primarily focused on timing.

The primary intent is to help make builds faster - or at least help understand how improvements could be made.

Clang outputs a set of diagnostic data (when adding -ftime-trace to CFLAGS) which gives detailed profile data for each compiled
source file. These source files can be viewed in Edge (edge://tracing) or Chrome (chrome://tracing) but only give a single view
of the compilation. The goal of the clangalyzer is to help analyze patterns across all the individual compiled source files.
This code does not look at any of the source code itself, intermediate build output data.

## Usage
Run
> ./clangalyzer.py --help

## Analysis Tools

It uses a pluggable approach so that different analysis tools can be plugged in. There are many built in tools. It also provides
a way to provide your own tools, in case there are non-generic tools which are interesting that you wish to run.

The default tools that come with are as follows:

##### [Tool] Gather Trace Tools
This tool "snapshots" the diagnostic data emitted by the compiler into the output path so they can be re-analyzed later.

##### [Tool] Output Target Times
This tool calculates the total time spent by all targets and summarizes them so you can see which targets take the most time to
compile.

##### [Tool] Serialize Project Trace
This tool takes all diagnostic data for all compiled files, and serializes them into a single diagnostic file which can then be
loaded in your favorite edge trace to help better visualize compilation for a given target.

##### [Tool] Show Build Folder Sizes
This tool calculates the build folder sizes.

##### [Tool] Show Precompiled Header Sizes
This tool calculates the sizes of just the precompiled headers in the build folder.

##### [Tool] Find Most Expensive Files
This tool details which files take the longest to compile.

##### [Tool] Find Most Expensive Includes
This tool finds the header files which are included the most and take the longest to include.

##### [Tool] Clang Breakdown
This tool gives a summary of everything that clang is doing and aggregates all of the time together.

### Implementing your own Tool
First, decide if this is a generic tool that can be used in any project, or one specific to your project. Hopefully
it can be configured in a way that can be generic.

Then, decide whether it should be opt in/opt out by default. All generic tools should be opt out, unless it has a large
performance implication. Alternatively, have expensive features of your tool be opt-in.

Start with tool.py as a template, and then look at the other tools to get a rough sense about how to implement it all.

Add it to all_tools() function in the clangalyzer (assuming it is generic).

## Tracking Data Over Time
One of the helpful ways that this script makes builds faster is by keeping track of some basic summary data. This summary
data is then serialized at the end of each run. During the next run, it will automatically compare against the previous run's
summary data and output whether or not items got better or worse. (The exact previous summary data to compare against is
configurable). Each tool decides the basic summary data to output - and when comparing, has the opportunity to output the summary
data.

## Future Improvements/Glaring Deficiencies

- Output summary as HTML.
- Tests
- Quiet mode doesn't work well

# Concerns

According to [Wikipedia](https://en.wikipedia.org/wiki/Concern_(computer_science)),

> In computer science, a concern is a particular set of
> information that has an effect on the code of a computer
> program.  A concern can be as general as the details of
> database interaction or as specific as performing a
> primitive calculation, depending on the level of
> conversation between developers and the program being
> discussed.  IBM uses the term concern space to describe
> the sectioning of conceptual information. 

This folder contains concerns whose details are unimportant
to the main bot code.  For example, the main code does not
need to know *how* to draw a leaderboard.  Instead, it will
delegate this task to `concerns.user_stat.leaderboard()`.
This offers useful abstractions.

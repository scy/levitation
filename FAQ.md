The FAQ was once in the project repository. At some point, it moved to the wiki. After Levitation was abandoned, the wiki was shut down.

This file consists of the contents of the FAQ as [recorded by the Internet Archive on August 6, 2010](http://web.archive.org/web/20100806233712/http://levit.at/ion/wiki/FAQ), reformatted into Markdown, updating or removing links where appropriate. The original content starts below this sentence.

# FAQ

_Todo: This is (at least partially) a first person style text, probably because it has been imported from Scytale’s import.py documentation. It should be rewritten to reflect that this is now a community project._

Since Levitation is not only a software project, but also the first effort to create something like “a new era for Wikipedia”, namely by allowing multiple, different articles under the same title, and by allowing distributed work, we are also asked a lot about our plans regarding this future Wikipedia structure. Therefore this FAQ also contains answers to some of those questions.

## Questions concerning the new Wikipedia era

### What is Omnipedia?

Omnipedia is a fictional website introduced by Scytale that serves as an example for how this new Wikipedia model could work.

### In your model, will every contributor need a Git clone of the whole Omnipedia?

No. In fact, I (Scytale) am suggesting that there will be a central web site, just like it is right now. But every registered user will have his or her own branch to create content in. And to facilitate easy forking and merging, access via Git should be possible.

You may compare it to [identi.ca](http://identi.ca/) and [StatusNet](http://status.net/): You have the possibility to run the software on your own machine, but you are not forced to, and most users simply use the central site.

### What will be the default branch to show if a new user visits the site for the first time?

There are several possible approaches, and we’re interested in your opinion on all of them (contact us).

*The “most popular” approach:* For anonymous users, the version that most of the registered users have in their Omnipedias is displayed. The user receives a hint that there are other versions available, ordered by popularity.
*The “recommended users” approach:* A new user is first greeted with a selection of about five different, popular users, including a one-line description on what is special about that person’s branch. The user may then select which person’s branch (s)he wants to see.

There are probably more possible approaches. Suggest one!

## Questions concerning Levitation

### What’s the project’s current status?

Have a look a the “Things that work” section in the README.

If you’re interested in how active the project is, check the commit history on http://github.com/scy/levitation/

### Why did you choose the name “Levitation”?

Actually, the name has not been chosen by carefully thinking about it for two weeks. Instead, the original name was “Gitipedia”, which, frankly, sucks. Another one had to be found, and after like five seconds I decided to name it Levitation.

The name symbolizes the feeling of a mass of content leaving its constraints and boundaries to be free and easily available.

### So, you’re running MediaWiki with Git as backend?

No. Currently, Levitation has nothing to do with running MediaWiki at all. I seriously doubt it is worth the effort to adapt MediaWiki for a Git backend. Instead, a new frontend should be developed.

### Okay, so you’re planning to fork Wikipedia?

Me? Probably not. But I know some guys who might be interested in doing it. And since I think that yet another centralistic Wikipedia is not the solution, I’m experimenting in a different direction. Namely, a distributed Wikipedia.

### Is there already a frontend software for Levitation’s repositories?

Not really. Currently some people are working on different projects in pre-alpha state, for example https://github.com/poelzi/communiki. There’s nothing usable yet, which might have something to do with the fact that we’re not even sure yet whether real Git repositories are the way to go, and the output format Levitation produces also isn’t written in stone yet.

Some CCC folks, including Felix von Leitner (Fefe), are thinking about hacking together something based on [gatling](http://www.fefe.de/gatling/), but are still in planning phase at the moment.

### But with Git, won’t every contributor need gigabytes of history?

First, if you haven’t heard about “git clone --depth” yet, have a look at it.

Second, my vision is to have 5 to 20 “Wikipedias” per language that focus on different aspects and have different policies. These would be hosted by someone having enough resources to do that, and editing articles would be done via a web interface as it is now.

The difference to today is that the Wikipedias can easily transfer content between each other, including history and using Git’s powerful merging capabilities. Additionally, everyone who wants to clone the whole Wikipedia can do it, with full history, and without waiting for a monthly dump. Instead, pulling from Wikipedia gives you the content as it was at that second.

Also, Git developers are currently working on the possibility to retrieve just parts of the repository.

### Wouldn’t it be better to split the data into several repositories?

(also: _Why don't you split up the repository into multiple branches, or even one branch / repo per article?_)

I can’t think of a good way to do that. Where do you draw the line?

Most people suggest “one repo per article”. That’s probably the best “line” there is, but how would you then move/rename/merge articles without losing history?

Also, because of the way git-fast-import works, importing into several repositories at the same time is not trivial.

Currently, this project is about mapping a MediaWiki history to a Git history while losing as litte information as possible. As soon as that works, we could think about using git-filter-branch or something like that to split it into saner chunks.

#### Alternative answer:

This question regularly comes up when discussing huge wikis (like dewiki) and why they aren't yet imported. Or when talking about the future handling of such repos.

The strongest reason might be: we want to maintain the _chronological integrity_. E.g. we want the possibility to checkout the german Wikipedia as it was on a specific date or a certain number of edits ago. The most popular examples are: "Show me the Wikipedia as it was before 9/11 (that is, 2001-09-10)" and "How did it look 1 million revisions ago".

There are many ideas how to handle these things after the import to git:

 * via submodules
 * let the frontend handle the checking out of all repos to the date
 * do something with merges
 * etc.

These things may all be workable, but we would prefer to let git handle that.

So, at the moment we try to persuade git to import huge wikis. If that really, really won't work, we will look at the other ideas.

### Would Levitation allow to incrementally import changes made in the current centralistic Wikipedia into one’s local Git clone?

I think so. There are some possible issues though.

If, for example, you would update only one article’s history and then another one’s, history would be in the wrong order and need to be rewritten. Git can do that easily, but the incremental importing tool would have to consider that.

Another problem could be that articles you have in your local clone might get deleted upstream. If they are, they no longer show up in dumps at all.

### Would Levitation allow it to make changes to the local clone and maintain these changes even when importing new stuff from the current centralistic Wikipedia?

Yes, that’s something that happens all the time in distributed development. Keep the upstream Wikipedia in one branch, your changes in another, and frequently rebase or merge. With things like git-rerere, you can minimize the amount of manual merging conflicts.

### Would Levitation allow it to make changes to the local clone and push them back to the current centralistic Wikipedia?

Absolutely, just like git-svn does. Nobody has written that code yet, and I doubt that I will do it, but it should be pretty straightforward.

### It looks to me as if importing gets slower and slower the more recent the commits become, right?

Maybe a bit (because the trees get larger), but actually not as much as you probably think. Levitation shows you the date in history while it writes the commits, and indeed the time it takes to finish one day is apparently increasing. However, for most Wikipedias, the number of commits per day is constantly increasing, so there’s simply more work to do per day.

### Where can I meet you guys and talk to you in person?

For example at the 26C3.

### Why are you doing this anyway?

Because I love Git and the development model DVCSs allow, because I’m fed up with de.wikipedia’s attitudes on policy and because I think using Git is one of the better solutions. I would hate it if other people developed another software that’s essentially as flawed as the current Wikipedia model.

### Me too, how can I help or say “thank you”?

Writing, improving and debugging Levitation is a considerable amount of work. Unpaid work, and the main developer is a pretty broke student. Your donations will help pay external hard drives to import larger Wikipedias, and basic stuff like paying the rent.

If you don’t want to give money, you have plenty of other options:

 * Play around with it and tell us about your experience.
 * If you’re good at Python, rewrite some of the code to be less ugly. One commit per change please, Scytale’s a control freak.
 * If you’re a Git guru, we’d love some hints about how to make the resulting repo smaller and improve overall performance. If you know a Git guru, ask him.
 * If you own a powerful box, import a large wiki and get in touch with us, we’re interested in size and performance.
 * Implement some of the still missing features or improve performance. Please ask us in advance before doing larger changes to avoid your patch getting rejected.
 * Check out the [todo list](http://web.archive.org/web/20100806233712/http://levit.at/ion/wiki/Category:Todo) or contact us and ask.
 * Spreading the word about Levitation is an option as well. So, write blog posts or talk to people on Git and Wikipedia mailing lists about the project.

### I have a question that’s not answered here.

Edit this page and enter a new question.

## About import.py

### It says “warning: trimming 257 bytes long text”…

This happens from time to time. The problem is, we only allow metadata (article names, change summaries, author names) to contain at most 255 bytes of content. This usually works quite well, because MediaWiki’s database has the same 255 byte restriction for those values. However, we noticed that in the XML dumps there are sometimes more than 255 bytes for a single metadata value. There may be several reasons for that. We currently know about one:

If you try to write an UTF-8 string longer than 255 bytes into the database, it will be truncated by the database server. However, since the database probably doesn’t know (or care about) the fact that these random bytes are actually UTF-8 text, the truncation might happen not on a character boundary, but in the middle of a multi-byte character, thus creating an invalid UTF-8 sequence. When the XML dumps are created, the XML writer refuses (rightly so) to write invalid UTF-8 sequences into the dump. Instead, it will insert the Unicode Replacement Character (U+FFFD) to indicate an invalid UTF-8 sequence in the input. Now, if the original truncation happened after the first byte of the character, the database entry will be 255 bytes long, with the last byte being invalid. When the replacement character is inserted, that last byte is replaced by U+FFFD, which maps to the three UTF-8 bytes ef bf bd. The data is therefore now 255 - 1 +3 = 257 bytes long and does not fit into our metadata storage.

The warning includes a hex representation of the string that has been truncated. If it ends in something else than ef bf bd, please contact us, because you have found another reason for truncation.

### It says “DeprecationWarning: struct integer overflow masking is deprecated”.

This is a known issue, but nothing serious. It has been fixed in [c7bbaa2](https://github.com/scy/levitation/commit/c7bbaa29545f16187f01aac8b0f9a7c0d51a544d) and [543ddd9](http://github.com/scy/levitation/commit/543ddd97b51c45b915eb53db464c7b5dae4b6922).

### This importer is really slow. Is there a better one?

Yes. There is. Have a look at [Levitation-perl](https://github.com/sbober/levitation-perl) by sbob

## Progress of the project

### What is the largest wiki you managed to import?

Reports for the largest wiki imported so far are known for vowiki. Import step 1 has been reported to work for jawiki and dewiki.

### Why isn't there a working repository for ${largewiki} yet?

The second step is still really slow. Maybe you could help optimizing it?

### I can't find a dump of enwiki?

We couldn't neither. Maybe (faint hope) there will be one soon ...

## About this site

### Isn’t it ironic that you’re using MediaWiki to document a project that will deprecate MediaWiki?

It’s like rain on your wedding day.

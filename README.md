# PLEASE NOTE: THIS PROJECT IS NO LONGER MAINTAINED

## The current state of the Levitation project

Levitation is a software project which, as a preparation for a decentralized Wikipedia, converts MediaWiki XML dump files into Git repositories, creating a Git commit for each wiki edit.

It has been abandoned by its original author, Tim Weber (aka Scytale or scy, the same person who wrote this overview page you’re currently reading), in 2009. The reason for that was that Tim lacked the time to work on it any further, and no significant contributions from other people were made.

However, since then, other people have worked on the codebase, since the original Leviation is free software and anyone is allowed to modify it:

 * Rüdiger Ranft has ported Levitation to the C language (instead of Python). His project is called ›elevation‹ and can be found at https://bitbucket.org/_rdi_/elevation
 * Christopher Corley has ported the code to Python 3, added IPv6 support and wants to work on it actively in 2015. Find his fork at https://github.com/cscorley/levitation
 * There are also some other forks on GitHub by people who have not contacted me (or I’ve forgotten about it). Check out the list of forks at https://github.com/scy/levitation/network

If you have questions about Levitation, want to work on it or need support, I’d prefer you ask one of the two other guys first. You can also try contacting me (see http://scy.name/contact), but I might refuse to help (or even reply to) you if it takes too much time or effort. I am no longer maintaining Levitation anymore, I’m sorry.

This note was originally written in March 2015 and updated in January 2017.

# PLEASE NOTE: THIS PROJECT IS NO LONGER MAINTAINED



What follows is the last version of the README, updated to the project's abandoned state.

    This is Levitation, a project to convert Wikipedia database dumps into Git
    repositories. It has been successfully tested with a small Wiki
    (bar.wikipedia.org) having 12,200 articles and 104,000 revisions. Importing
    those took 6 minutes on a Core 2 Duo 1.66 GHz. RAM usage is minimal: Pages
    are imported one after the other, it will at most require the amount of memory
    needed to keep all revisions of a single page into memory. You should be safe
    with 1 GB of RAM.
    
    See below (“Things that work”) for the status at the time it was abandoned.
    
    Some knowledge of Git is required to use this tool. And you will probably
    need to edit some variables in the source code.
    
    You need at least a 2.5 Python, my tests run with 2.6.
    
    
    How it should be done:
    
    You can get recent dumps of all Wikimedia wikis at:
    http://download.wikimedia.org/backup-index.html
    
    The pages-meta-history.xml file is what we want. (In case you’re wondering:
    Wikimedia does not offer content SQL dumps anymore, and there are now full-
    history dump for en.wikipedia.org because of its size.) It includes all pages
    in all namespaces and all of their revisions.
    
    Alternatively, you may use a MediaWiki’s “Special:Export” page to create an XML
    dump of certain pages.
    
    
    Things that work:
    
     - Read a Wikipedia XML full-history dump and output it in a format suitable
       for piping into git-fast-import(1). The resulting repository contains one
       file per page. All revisions are available in the history. There are some
       restrictions, read below.
    
     - Use the original modification summary as commit message.
    
     - Read the Wiki URL from the XML file and set user mail addresses accordingly.
    
     - Use the author name in the commit instead of the user ID.
    
     - Store additional information in the commit message that specifies page and
       revision ID as well as whether the edit was marked as “minor”.
    
     - Use the page’s name as file name instead of the page ID. Non-ASCII
       characters and some ASCII ones will be replaced by “.XX”, where .XX is their
       hex value.
    
     - Put pages in namespace-based subdirectories.
    
     - Put pages in a configurably deep subdirectory hierarchy.
    
     - Use command line options instead of hard-coded magic behavior. Thanks to
       stettberger for adding this.
    
     - Use a locally timezoned timestamp for the commit date instead of an UTC one.
    
    
    Things that are still missing:
    
     - Allow IPv6 addresses as IP edit usernames. (Although afaics MediaWiki itself
       cannot handle IPv6 addresses, so we got some time.)
    
    
    Things that are strange:
    
     - Since we use subdirectories, the Git repo is no longer larger than the
       uncompressed XML file, but instead about 30% of it. This is good. However,
       it is still way larger than the bz2 compressed file, and I don’t know why.
    
    
    Things that are cool:
    
     - “git checkout master~30000” takes you back 30,000 edits in time — and on my
       test machine it only took about a second.
    
     - The XML data might be in the wrong order to directly create commits from it,
       but it is in the right order for blob delta compression: When passing blobs
       to git-fast-import, delta compression will be tried based on the previous
       blob — which is the same page, one revision before. Therefore, delta
       compression will succeed and save you tons of storage.
    
    
    Example usage:
    
    Please note that there’s the variable IMPORT_MAX, right at the beginning of
    import.py. By default it’s set to 100, so Levitation will only import 100
    pages, not more. This protects you from filling your disk when you’re too
    impatient. ;) Set it to -1 when you’re ready for a “real” run.
    
    This will import the pdc.wikipedia.org dump into a new Git repository “repo”:
    
      rm -rf repo; git init --bare repo && \
        ./import.py < ~/pdcwiki-20091103-pages-meta-history.xml | \
        GIT_DIR=repo git fast-import | \
        sed 's/^progress //'
    
    Execute “import.py --help” to see all available options.
    
    
    Storage requirements:
    
    “maxrev” be the highest revision ID in the file.
    
    “maxpage” be the highest page ID in the file.
    
    “maxuser” be the highest user ID in the file.
    
    The revision metadata storage needs maxrev*17 bytes.
    
    The revision comment storage needs maxrev*257 bytes.
    
    The author name storage needs maxuser*257 bytes.
    
    The page title storage needs maxpage*257 bytes.
    
    Those files can be deleted after an import.
    
    Additionally, the content itself needs some space. My test repo was about 15%
    the size of the uncompressed XML, that is about 300% the size of the bz2
    compressed XML data (see “Things that are strange”).
    
    Note that if you want to check out a working copy, the filesystem it will be
    living on needs quite a few free inodes. If you get “no space left on device”
    errors with plenty of space available, that’s what hit you.
    
    
    Contacting the author:
    
    This monster was written by in 2009 by Tim “Scytale” Weber (today aka “scy”). It
    was an experiment, whether the “relevance war” in the German Wikipedia at that
    time can be ended by decentralizing content. It is no longer actively maintained
    by me.
    
    
    This whole bunch of tasty bytes is licensed under the terms of the WTFPLv2.

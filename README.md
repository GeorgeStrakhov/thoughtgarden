# ThoughtGarden

Cicero said: "If you have a garden and a library, you have everything you need". Well, given that most our content sources are digital these day and that (sadly?) most of us end up gardening ideas rather than vegetables - I was wondering whether the garden and the library really have to be two distinct things.

ThoughtGarden (a.k.a. TGN) is an experiment at merging a garden and a library. It's opinionated, minimalistic, open source and self-hosted (it's your garden after all). It's important to clarify that unlike projects like Obsidian and many others, TGN is **not** meant to help you organize your ideas. It's here to help you keep other people's ideas that you like.

TGN provides an interface for other applications (e.g. your text editor, or note taking app), so that when you are thinking up your own thoughts - you can easily reach out to your garden and find the right ingredient. Nothing stops you from adding your own thinking to your thought garden. But it's generally advisable to do it after it has been formed, not while you are still working on it.

## Here is how TGN works:

1. first, you set up your garden (You can run it locally, or on a server somewhere in the cloud. You'll need python and postgres at the very least. Ideally also a media storage like S3. You will also need to decide which embedding model to use for storing and searching ideas.)

2. then, whenever you find a piece of content (a youtube/vimeo video, an audio recording of an interview, a book or paper in PDF, a blogpost or any other webpage) - you simply add a link to it, or upload it.

3. TGN's smarts then take care of the rest:

    - the piece of content is downloaded and saved in your own media storage - because you can't ever trust the internet to persist your favorite links.
    - a "screenshot" is taken of your content that can be used as a thumbnail image in search results etc.
    - for videos: full transcript is either downloaded from youtube or created from scratch using a speech-to-text model of your choice (e.g. whisper)
    - all the text (from the pdf, webpage or video/audio transcript) is broken down into paragraphs, an embedding is created from each paragraphs - to facilitate future search and RAG
    - meaningful metadata is automatically extracted (if possible) by an LLM (authors, language, topics, tags, year etc.)
    - everything is stored in a database (by default postgres with pgvector)

4. From now on, the idea is forever safely captured in your private thought garden. You can query and find thoughts semantically (via a web interface or an API), you can share your garden with friends (think of it as a self-hosted blog / links space) etc. If you are sharing - make sure to only invite select friends. Thought gardens are not meant to be public, high-traffic places on the web but rather intimate spaces. Also when sharing, storing and uploading - remember that you are responsible for all potential copyright issues.

## For now ThoughtGarden is just a thought

I'm planning to start building (growing?) it slowly for my own use. Planning to use the tech stack I'm most familiar with: Docker, Python, Django, postgres + pgvector, Vue3. But maybe it's worth exploring other choices? Oh, and should there be others interested in the same kind of thing - contributions are very welcome. After all, what could be better than growing a garden with a friend?

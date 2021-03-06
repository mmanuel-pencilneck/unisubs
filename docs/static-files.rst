Static Files
============

The static files pipeline for unisubs has two goals:

- Combine & compress files that are used together (e.g. one html page linking
  to many css filed)
- Make sure every time media is processed we have each file with a unique name.
  This allows us to the set the expire header to the far future, meaning that
  it will be aggressively cached.
- Each new release won't be cached by clients, since the URLS for each release
  are unique

Quick Start
-----------

1. When in development with ``DEBUG = True`` all media will not be compressed.
   Else you can controle this with the ``COMPRESS_MEDIA`` setting.
2. You can add media to the any of the bundles on ``settings.py`` or create a
   new bundle if you need a specific collection of media (see bellow)
3. If it's a new bundle add the include in the template (see bellow)

When you want to test the compiled version:

1. Set ``DEBUG`` to false
2. Run the ``compile_config``, ``compile_statwidgetconfig``, ``compile_media``
   commands.
3. Run ``deploy/create_commit_file``
4. Run the ``compile_media`` command

Compilation & Minification
--------------------------

``settings.py`` has a ``MEDIA_BUNDLES`` dictionary. Each key sets an id (a
unique name for the bundle), with the following properties:

- **type**: Can be ``'css'`` or ``'js'`` for now
- **files**: a sequence of files to be processed. Files will be processed in
  the order in which they're are defined on the bundle. They're path should be
  relative to the STATIC_URL (i.e. unisubs/media)
- **closure_deps**: File (inside js) that holds the closure dependencies list.
- **debug**: If true will include the ``closure-debug-dependencies.js``.
- **include_flash_deps**: boolean
- **optimizations**: defaults to closure's more agreesive mode
  (``ADVANCED_OPTIMIZATIONS``) else can be set to ``SIMPLE_OPTIMIZATIONS``.

Files will be concatenated in the order in which they are defined.

JS will be compiled by the closure compiler at ``closure/compiler.jar``.

CSS will be compressed with the YUI compressor at
``css-compression/yuicompressor-2.4.6.jar``. For css we are only minifying, but we
are not changing anything that might break the site.

In Templates
------------

In templates, instead of liking to the the individual css or js files, you'd
simply:

.. code-block:: django

    {% load  media_compressor %}
    {% include_bundle "[bundle name - the key in MEDIA_BUNDLE]" %}

If ``CSS_USE_COMPILED`` is ``True`` the link to that bundle compressed file
will be inserted. Else we'll add the original urls. If a ``CSS_USE_COMPILED``
is not set, it will default to the oposite of ``settings.DEBUG``.

Compiling
---------

Compiling should be done with ::

    $ manage.py compile_media --settings=[settings file] [bundle-name(s)]

If you pass one or more bundle names as arguments to the command it will only
compile those bundles (useful for testing / debugging), else all bundles will
be compiled. Just make sure that you have run ``compile_conf`` and friends and
also the ``deploy/create_commit_file.py`` before doing so.

When the ``--verbosity`` param is set to 2, ``compile_media`` will output the
cmd_strings passed to the compilers.

Directory layout
----------------

Inside ``MEDIA_ROOT`` media will be compiled to ``static-cache/[hash of latest
git commit]/``. For example,
``MEDIA_ROOT/static-cache/21a1bbcc/js/unisubs-onsite-compiled.js``.

This way we use one unique identifier for each revision, in fact, we relly on
the one git gives us, which has the added benefit of making it easier to
troubleshoot revisions and verify that links are correct.

Static cache is never in source control and should not be the storage path for
anything. Its sole purpose is to be a disposable place where media can be
compiled and moved to a unique URL.

Relevant Settings
-----------------

These need to be defined in ``settings.py``:

.. attribute:: STATIC_URL

    Since the location of media is no longer static, the ``STATIC_URL`` takes
    into consideration the new directory layout. Every time a new git version
    is running and ``deploy/create_commit_file.py`` is ran, the ``STATIC_URL``
    will change (and) therefore you need to restart the sever/reload app coder
    for that to take effect.

.. attribute:: COMPRESS_YUI_BINARY

    The path, relative to the unisubs dir where the YUI compressor jar
    lives(``java -jar ./css-compression/yuicompressor-2.4.6.jar``)

.. attribute:: COMPRESS_MEDIA

    When true media will be compressd / packed, Both CSS and JS. The default
    value for this is the oposite of ``DEBUG``.

.. attribute:: COMPRESS_OUTPUT_NAME

    The directory that holds the root to the static cache, i.e. where all
    compiled and version specific media will be copyed to (see dir layout
    above). Defaults to 'static-cache'.

.. attribute:: STATIC_URL_BASE

    This is the media url before appending the commit hash. This is useful in
    places where you need the media base to an external stable url , for example on
    the embed and widgetizer (which never change).

Serving Media
-------------

On the local development machine or the dev environment media is stored locally
in the file disk. Staging and production with Amazon's s3, so in those
environments media needs to be copied to s3.

This is achieved by calling::

    $ manage.py send_to_s3 --settings=[settings module]

Which is part of the update_static fabric command. That command requires the
``USE_AMAZON`` set (needs correct values for secret, id and bucket), and it
will:

- Move the entire content of ``MEDIA_ROOT/static-cache/[hash guid]``.
  All of these will have far future expire headers.
- Copy and create the files that are used externally (in offsite widgets),
  namely: ``js/unisubs-widgetizer.js``,
  ``js/widgetizer/widgetizerprimer.js"]`` to ``MEDIA_ROOT/js/...``.
  These do not have far future expire headers.

All files above 1kb will be served with gzip compression (smaller files tend to
actually inflate).

TODOS
-----

- Remove all lingering instances of ``include _js_onsite...``
- Make compilation fail on any error.
- Find out how to fix warnings for jQuery and others
- Put all binaries that deal with media compression (closure compiler, yui
  compressor) on the same place

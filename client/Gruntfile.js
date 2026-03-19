module.exports = function(grunt) {
  let cssnano = require("cssnano"),
      fs = require("fs"),
      path = require("path"),
      superagent = require("superagent"),
      gettextParser = require('gettext-parser'),
      { pipeline } = require("stream"),
      yauzl = require("yauzl");

  const remoteFonts = [
    // plain file example (already working):
    {
      url: "https://github.com/satbyy/go-noto-universal/releases/download/v7.0/GoNotoKurrent-Regular.ttf",
      type: "file",
      output: "GoNotoKurrent-Regular.ttf",
    },

    // Inter zip → extract one file
    {
      url: "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip",
      type: "zip",
      pick: "extras/ttf/Inter-Regular.ttf",
      output: "Inter-Regular.ttf",
    },
  ];

  function downloadToFile(url, outPath, cb) {
    grunt.file.mkdir(path.dirname(outPath));

    const tmpPath = outPath + ".download";
    const stream = fs.createWriteStream(tmpPath);

    stream.on("finish", function () {
      try {
        fs.renameSync(tmpPath, outPath);
        cb(null);
      } catch (e) {
        cb(e);
      }
    });

    stream.on("error", function (e) {
      cb(e);
    });

    agent.get(url).pipe(stream);
  }

  // entryPath deve combaciare esattamente con il path dentro lo zip
  function extractZipEntry(zipPath, entryPath, outPath, cb) {
    try {
      grunt.file.mkdir(path.dirname(outPath));
    } catch (e) {
      return cb(e);
    }

    yauzl.open(zipPath, { lazyEntries: true }, (err, zipfile) => {
      if (err) return cb(err);

      let done = false;
      const finishOnce = (e) => {
        if (done) return;
        done = true;
        try { zipfile.close(); } catch (_) {}
        cb(e || null);
      };

      zipfile.readEntry();

      zipfile.on("entry", (entry) => {
        // Normalizza a slash (gli zip usano quasi sempre /)
        const name = entry.fileName;

        if (name !== entryPath) {
          return zipfile.readEntry();
        }

        // Se è una directory, non va bene
        if (/\/$/.test(name)) {
          return finishOnce(new Error(`ZIP entry is a directory: ${entryPath}`));
        }

        zipfile.openReadStream(entry, (err, rs) => {
          if (err) return finishOnce(err);

          const ws = fs.createWriteStream(outPath);
          pipeline(rs, ws, (err) => finishOnce(err || null));
        });
      });

      zipfile.on("end", () => {
        // Finito di scorrere entries senza match
        if (!done) finishOnce(new Error(`ZIP entry not found: ${entryPath}`));
      });

      zipfile.on("error", finishOnce);
    });
  }

  class SimpleGettext {
    constructor() {
      this.catalogs = {};   // { lang: { domain: { msgid: msgstr } } }
      this.locale = 'en';
      this.domain = 'messages'; // default gettext domain
    }

    /**
     * Add PO data for a language and domain.
     * @param {string} lang - language code (e.g. 'en')
     * @param {string} domain - domain name (e.g. 'stable')
     * @param {object|string} poData - parsed object or raw PO text
     */
    addTranslations(lang, domain = 'messages', poData) {
      if (typeof poData === 'string') {
        poData = gettextParser.po.parse(poData);
      }

      if (!this.catalogs[lang]) this.catalogs[lang] = {};
      if (!this.catalogs[lang][domain]) this.catalogs[lang][domain] = {};

      const entries = poData.translations || {};
      for (const ctx of Object.keys(entries)) {
        for (const msgid of Object.keys(entries[ctx])) {
          if (!msgid) continue; // skip header
          const entry = entries[ctx][msgid];
          const msgstr = entry.msgstr && entry.msgstr[0];
          if (msgstr && msgstr.trim()) {
            this.catalogs[lang][domain][msgid] = msgstr;
          }
        }
      }
    }

    /**
     * Set the current active language.
     */
    setLocale(lang) {
      this.locale = lang;
    }

    /**
     * Set the active text domain (for compatibility).
     */
    setTextDomain(domain) {
      this.domain = domain;
    }

    /**
     * Translate a message ID.
     * Returns the original if no translation is found.
     */
    gettext(msgid) {
      const langCat = this.catalogs[this.locale];
      if (!langCat) return msgid;
      const domainCat = langCat[this.domain];
      if (!domainCat) return msgid;
      return domainCat[msgid] || msgid;
    }
  }

  require('load-grunt-tasks')(grunt);

  async function loadGettextParser() {
    return await import('gettext-parser');
  }

  grunt.initConfig({
    clean: {
      all: ["build", "tmp", "dist"],
      tmp: ["tmp", "dist", "instrument"],
    },

    copy: {
      build: {
        files: [
          {dest: "tmp/", cwd: "dist", src: ["**"], expand: true},
          {dest: "tmp/css/", cwd: "dist", src: ["fonts.css*"], expand: true, flatten: true},
          {dest: "tmp/css/", cwd: "dist", src: ["styles.css*"], expand: true, flatten: true},
          {dest: "tmp/js/", cwd: "dist", src: ["main.js*"], expand: true, flatten: true},
          {dest: "tmp/js/", cwd: "dist", src: ["polyfills.js*"], expand: true, flatten: true},
          {dest: "tmp/js/", cwd: "dist", src: ["runtime.js*"], expand: true, flatten: true},
          {dest: "tmp/js/", cwd: "dist", src: ["vendor.js*"], expand: true, flatten: true}
        ]
      },

      package: {
        files: [
          {dest: "build/css", cwd: "tmp/css", src: ["**"], expand: true},
          {dest: "build/fonts", cwd: "app/fonts", src: ["**"], expand: true},
          {
            dest: 'build/fonts',
            cwd: 'node_modules/',
            src: ['@fontsource*/**/files/*normal*woff2'],
            flatten: true,
            expand: true
          },
          {dest: "build/images", cwd: "app/images", src: ["**"], expand: true},
          {dest: "build/js", cwd: "tmp/js", src: ["**"], expand: true},
          {dest: "build/js/", cwd: "tmp/", src: ["chunk-*.js*"], expand: true},
          {dest: "build/data", cwd: "tmp/assets/data", src: ["**"], expand: true},
          {dest: "build/viewer/", cwd: ".", src: ["app/viewer/*"], expand: true, flatten: true},
          {dest: "build/index.html", cwd: ".", src: ["tmp/index.html"], expand: false, flatten: true},
          {dest: "build/license.txt", cwd: ".", src: ["../LICENSE"], expand: false, flatten: true},
        ]
      },

      instrument: {
        files: [
          {dest: "dist", cwd: "instrument/", src: ["**"], expand: true}
        ]
      },

      coverage: {
        files: [{
          dest: "build/",
          cwd: "app/",
          src: [
            "**",
            "!js/**/*.js",
            "lib/js/*.js",
            "lib/js/locale/*.js"
          ],
          expand: true
        }]
      }
    },

    "string-replace": {
      pass1: {
        files: {
          "tmp/index.html": "tmp/index.html"
        },

        options: {
          replacements: [
            {
              pattern: /<script src="/g,
              replacement: "<script src=\"js/"
            },
            {
              pattern: /<link rel="stylesheet" href="/g,
              replacement: "<link rel=\"stylesheet\" href=\"css/"
            },
            {
              pattern: /.\/media\//gi,
              replacement: function () {
                return "../fonts/";
              }
            }
          ]
        }
      },
      pass2: {
        files: {
          "tmp/css/styles.css": "tmp/css/styles.css",
          "tmp/css/fonts.css": "tmp/css/fonts.css"
        },

        options: {
          replacements: [
            {
              pattern: /.\/media\//gi,
              replacement: function () {
                return "../fonts/";
              }
            }
          ]
        }
      }
    },

    confirm: {
      "pushTranslationsSource": {
        options: {
          // Static text.
          question: "WARNING:\n"+
              "this task may cause translations loss and should be executed only on stable branch.\n\n" +
              "Are you sure you want to proceed (Y/N)?",
          input: "_key:y"
        }
      }
    },

    postcss: {
      build_css_with_ltr_rtl_combined: {
        options: {
          processors: [
            require('postcss-rtlcss')(),
            cssnano({ preset: 'default' }) // Minify CSS
          ]
        },
        src: 'tmp/css/styles.css',
        dest: 'tmp/css/styles.css'
      },
    },

    webpack: {
      crypto_worker: {
        entry: {
          'crypto.worker.js': './app/workers/crypto.worker.ts',
        },
        output: {
          filename: 'crypto.worker.js',
          path: path.resolve('build/workers/'),
          libraryTarget: 'umd',
          globalObject: 'this',
        },
        mode: 'production',
        resolve: {
          fallback: {
            fs: false,
            crypto: false,
            path: false,
            stream: false
          }
        }
      },
      pdfjs: {
        entry: {
          'script.min.js': './app/viewer/script.js',
        },
        output: {
          filename: '[name]',
          path: path.resolve('app/viewer/'),
          libraryTarget: 'umd',
          globalObject: 'this', // This makes the bundle work in both browser and Node.js
        },
        mode: 'production',
      }
    },

    shell: {
      build: {
        command: "npx ng build --configuration=production"
      },
      build_for_testing: {
        command: "npx ng build --configuration=testing"
      },
      instrument: {
        command: "nyc instrument dist --in-place"
      },
      brotli_compress: {
        command: 'find . -type f -not -name \'index.html\' -not -path \'./data/*\' -not -path \'./fonts/*\' -not -path \'./images/*\' -exec brotli -q 11 {} --output={}.br \\;',
        options: {
          execOptions: {
            cwd: './build'
          }
        }
      }
    },
  });

  let readNoTranslateStrings = function() {
    return JSON.parse(grunt.file.read("app/assets/data_src/notranslate_strings.json"));
  };

  let notranslate_strings = readNoTranslateStrings();

  function str_escape(val) {
    if (typeof(val) !== "string") {
      return val;
    }

    return val.replace(/[\n]/g, "\\n").replace(/[\t]/g, "\\r");
  }

  function str_unescape(val) {
    if (typeof(val) !== "string") {
      return val;
    }

    return val.replace(/\\n/g, "\n").replace(/\\t/g, "\t");
  }

  let agent = superagent.agent(),
      sourceFile = "app/assets/data_src/pot/en.po"

  function readWeblateToken() {
    return (process.env.WEBLATE_TOKEN || "").trim();
  }

  // Weblate instance configuration (safe to commit)
  const weblateUrl = "https://localizationlab.weblate.cloud";
  const weblateProject = "globaleaks";
  const weblateComponent = "stable";
  const weblateSourceLang = "en";

  // Secret (must come from environment)
  const weblateToken = readWeblateToken();

  function weblateApi(pathname) {
    return `${weblateUrl}/api${pathname}`;
  }

  function weblateAuthHeaders() {
    return { "Authorization": "Token " + weblateToken };
  }

  function extractLangCodeFromTranslationItem(item) {
    // Weblate may serialize language as:
    // - item.language_code: "it"
    // - item.language: "it" OR URL ".../languages/it/"
    // - item.language.code: "it"
    if (!item) return null;

    if (typeof item.language_code === "string") return item.language_code;
    if (item.language && typeof item.language.code === "string") return item.language.code;

    if (typeof item.language === "string") {
      if (item.language.indexOf("/") !== -1) {
        const m = item.language.match(/\/languages\/([^/]+)\/?$/);
        return m ? m[1] : null;
      }
      return item.language;
    }

    return null;
  }

  function listWeblateTranslationsAllPages(cb) {
    const firstUrl = weblateApi(`/components/${weblateProject}/${weblateComponent}/translations/`);
    let acc = [];

    function fetchPage(url) {
      agent.get(url)
        .set(weblateAuthHeaders())
        .end(function(err, res) {
          if (err || !res || !res.ok) {
            console.log("Error: " + (res ? res.text : err));
            return cb(err || new Error("Failed to list Weblate translations"));
          }

          let data;
          try {
            data = JSON.parse(res.text);
          } catch (e) {
            return cb(e);
          }

          if (Array.isArray(data.results)) acc = acc.concat(data.results);

          if (data.next) {
            return fetchPage(data.next); // data.next is usually absolute
          }

          cb(null, acc);
        });
    }

    fetchPage(firstUrl);
  }

  function downloadWeblatePo(langCode, cb) {
    const weblateLangCodeMap = {
      "fa_AF": "prs",
      "ku_IQ": "ckb_IQ",
      "sr_ME": "cnr",
      "sr_RS@latin": "sr_Latn",
      "ug@Cyrl": "ug@cyrl",
      "ug@Latin": "ug@latin",
      "zh_CN": "zh_Hans",
      "zh_HK": "zh_Hant_HK",
      "zh_TW": "zh_Hant"
    };

    let weblateLangCode = weblateLangCodeMap[langCode] || langCode;

    const url = weblateApi(`/translations/${weblateProject}/${weblateComponent}/${weblateLangCode}/file/`);
    grunt.file.mkdir("app/assets/data_src/pot");

    const outPath = `app/assets/data_src/pot/${langCode}.po`;
    const stream = fs.createWriteStream(outPath);

    stream.on("finish", function() { cb(null, outPath); });
    stream.on("error", function(e) { cb(e); });

    agent.get(url)
      .set(weblateAuthHeaders())
      .pipe(stream);
  }

  function uploadWeblateSourcePo(cb) {
    const url = weblateApi(`/translations/${weblateProject}/${weblateComponent}/${weblateSourceLang}/file/`);

    if (!fs.existsSync(sourceFile)) {
      console.log("Error: missing source file " + sourceFile + " (run grunt makeTranslationsSource first)");
      return cb(false);
    }

    agent.post(url)
      .set(weblateAuthHeaders())
      // method=source updates source strings
      .field("method", "replace")
      // optional: be tolerant with conflicts
      .field("conflicts", "ignore")
      .attach("file", sourceFile)
      .end(function(err, res) {
        if (err || !res || !res.ok) {
          console.log("Error: " + (res ? res.text : err));
          return cb(false);
        }
        cb(true);
      });
  }

  grunt.registerTask("fetchFonts", function () {
    const done = this.async();

    const destDir = "app/fonts";
    const tmpDir = "tmp/fonts";
    grunt.file.mkdir(destDir);
    grunt.file.mkdir(tmpDir);

    if (!Array.isArray(remoteFonts) || remoteFonts.length === 0) {
      console.log("fetchFonts: no remote fonts configured.");
      return done();
    }

    let i = 0;
    const next = () => {
      if (i >= remoteFonts.length) return done();

      const item = remoteFonts[i++];
      const outPath = path.join(destDir, item.output);

      if (item.type === "file") {
        console.log(`fetchFonts: downloading ${item.url} -> ${outPath}`);
        return downloadToFile(item.url, outPath, (err) => {
          if (err) {
            console.log(`fetchFonts: failed downloading ${item.url}: ${err}`);
            return done(false);
          }
          next();
        });
      }

      if (item.type === "zip") {
        const zipName = path.basename(item.url.split("#")[0].split("?")[0]);
        const zipPath = path.join(tmpDir, zipName);

        console.log(`fetchFonts: downloading ${item.url} -> ${zipPath}`);
        return downloadToFile(item.url, zipPath, (err) => {
          if (err) {
            console.log(`fetchFonts: failed downloading ${item.url}: ${err}`);
            return done(false);
          }

          console.log(`fetchFonts: extracting ${item.pick} -> ${outPath}`);
          extractZipEntry(zipPath, item.pick, outPath, (err2) => {
            if (err2) {
              console.log(`fetchFonts: failed extracting from ${zipName}: ${err2}`);
              return done(false);
            }

            // Optional cleanup
            try { fs.unlinkSync(zipPath); } catch (e) {}
            next();
          });
        });
      }

      console.log(`fetchFonts: unknown type for ${item.url}`);
      done(false);
    };

    next();
  });

  grunt.registerTask("makeTranslationsSource", async function() {
    const done = this.async();
    const gettextParser = await loadGettextParser();
    let data = {
      "charset": "UTF-8",
      "headers": {
        "project-id-version": "GlobaLeaks",
        "language-team": "English",
        "mime-version": "1.0",
        "content-type": "text/plain; charset=UTF-8",
        "content-transfer-encoding": "8bit",
        "language": "en",
        "plural-forms": "nplurals=2; plural=(n != 1);"
      },
      "translations": {
        "": {
        }
      }
    };

    let gt = new SimpleGettext(),
        translationStringRegexpJSON = /"en":\s?"(.+)"/gi;

    gt.setTextDomain("stable");

    function addString(str) {
      if (notranslate_strings.indexOf(str) !== -1) {
        return;
      }

      data["translations"][""][str] = {
        "msgid": str,
        "msgstr": str
      };
    }

    function extractStringsFromJSONFile(filepath) {
      let filecontent = grunt.file.read(filepath),
          result;

      result = translationStringRegexpJSON.exec(filecontent);
      while (result) {
        addString(result[1]);
        result = translationStringRegexpJSON.exec(filecontent);
      }
    }

    function extractStringsFromTXTFile(filepath) {
      let filecontent = grunt.file.read(filepath),
          lines = filecontent.split("\n");

      for (let i=0; i<lines.length; i++){
        // we skip adding empty strings and variable only strings
        if (lines[i] !== "" && !lines[i].match(/^{[a-zA-Z0-9]+}$/g)) {
          addString(lines[i]);
        }
      }
    }

    function extractStringsFromFile(filepath) {
      let ext = filepath.split(".").pop();

      if (ext === "json") {
        extractStringsFromJSONFile(filepath);
      } else if (ext === "txt") {
        extractStringsFromTXTFile(filepath);
      }
    }

    function extractStringsFromDir(dir) {
      grunt.file.recurse(dir, function(absdir, rootdir, subdir, filename) {
        let filepath = path.join(dir, subdir || "", filename || "");
        extractStringsFromFile(filepath);
      });
    }

    ["app/assets/data_src/texts.txt",
      "app/assets/data_src/appdata.json",
      "app/assets/data_src/field_attrs.json"].forEach(function(file) {
      extractStringsFromFile(file);
    });

    ["app/assets/data_src/questionnaires",
      "app/assets/data_src/questions",
      "app/assets/data_src/txt"].forEach(function(dir) {
      extractStringsFromDir(dir);
    });

    grunt.file.mkdir("app/assets/data_src/pot");

    fs.writeFileSync("app/assets/data_src/pot/en.po", gettextParser.po.compile(data), "utf8");

    console.log("Written " + Object.keys(data["translations"][""]).length + " string to app/assets/data_src/pot/en.po.");
    done();
  });

  grunt.registerTask("makeAppData", function() {
    const done = this.async();
    (async () => {
      const gettextParser = await loadGettextParser();
      let gt = new SimpleGettext(),
          supported_languages = [];

      gt.setTextDomain("stable");

      grunt.file.recurse("app/assets/data_src/pot/", function(absdir, rootdir, subdir, filename) {
        supported_languages.push(filename.replace(/.po$/, ""));
      });

      let appdata = JSON.parse(fs.readFileSync("app/assets/data_src/appdata.json")),
          output = {},
          version = appdata["version"],
          templates = appdata["templates"],
          templates_sources = {};

      let translate_object = function(object, keys) {
        for (let k in keys) {
          if (object[keys[k]]["en"] === "")
            continue;

          supported_languages.forEach(function(lang_code) {
            gt.setLocale(lang_code);
            let translation = gt.gettext(str_escape(object[keys[k]]["en"]));
            if (translation !== undefined) {
              object[keys[k]][lang_code] = str_unescape(translation).trim();
            }
          });
        }
      };

      let translate_field = function(field) {
        translate_object(field, ["label", "description", "hint"]);

        // Ensure attrs is an array before looping
        if (Array.isArray(field.attrs)) {
          field.attrs.forEach(function(attr) {
            translate_object(attr, ["value"]);
          });
        }

        // Ensure options is an array before looping
        if (Array.isArray(field.options)) {
          field.options.forEach(function(option) {
            translate_object(option, ["label"]);
          });
        }

        // Ensure children is an array before looping
        if (Array.isArray(field.children)) {
          field.children.forEach(function(child) {
            translate_field(child);
          });
        }
      };

      let translate_step = function(step) {
        translate_object(step, ["label", "description"]);

        if (Array.isArray(step.children)) {
          step.children.forEach(function(child) {
            translate_field(child);
          });
        }
      };

      let translate_questionnaire = function(questionnaire) {
        if (Array.isArray(questionnaire.steps)) {
          questionnaire.steps.forEach(function(step) {
            translate_step(step);
          });
        }
      };

      gt.addTranslations("en", "stable", gettextParser.po.parse(fs.readFileSync("app/assets/data_src/pot/en.po")));

      grunt.file.recurse("app/assets/data_src/txt", function(absdir, rootdir, subdir, filename) {
        let template_name = filename.split(".txt")[0],
            filepath = path.join("app/assets/data_src/txt", subdir || "", filename || "");

        templates_sources[template_name] = grunt.file.read(filepath);
      });

      supported_languages.forEach(function(lang_code) {
        gt.setLocale(lang_code);
        gt.addTranslations(lang_code, "stable", gettextParser.po.parse(fs.readFileSync("app/assets/data_src/pot/" + lang_code + ".po")));

        for (let template_name in templates_sources) {
          if (!(template_name in templates)) {
            templates[template_name] = {};
          }

          let tmp = templates_sources[template_name];

          let lines = templates_sources[template_name].split("\n");

          lines.forEach(function(line, i) {
            let translation = gt.gettext(str_escape(line));
            if (translation === undefined) {
              return;
            }

            if (line !== "" && !line.match(/^{[a-zA-Z0-9]+}/g)) {
              tmp = tmp.replace(line, str_unescape(translation));
            }
          });

          templates[template_name][lang_code] = tmp.trim();
        }
      });

      output["version"] = version;
      output["templates"] = templates;
      output["node"] = {};

      Object.keys(appdata["node"]).forEach(function(k) {
        output["node"][k] = {};
        supported_languages.forEach(function(lang_code) {
          gt.setLocale(lang_code);
          output["node"][k][lang_code] = str_unescape(gt.gettext(str_escape(appdata["node"][k]["en"])));
        });
      });

      output = JSON.stringify(output, null, 2);

      fs.writeFileSync("app/assets/data/appdata.json", output);

      grunt.file.recurse("app/assets/data_src/questionnaires", function(absdir, rootdir, subdir, filename) {
        let srcpath = path.join("app/assets/data_src/questionnaires", subdir || "", filename || "");
        let dstpath = path.join("app/assets/data/questionnaires", subdir || "", filename || "");
        let questionnaire = JSON.parse(fs.readFileSync(srcpath));
        translate_questionnaire(questionnaire);
        fs.writeFileSync(dstpath, JSON.stringify(questionnaire, null, 2));
      });

      grunt.file.recurse("app/assets/data_src/questions", function(absdir, rootdir, subdir, filename) {
        let srcpath = path.join("app/assets/data_src/questions", subdir || "", filename || "");
        let dstpath = path.join("app/assets/data/questions", subdir || "", filename || "");
        let field = JSON.parse(fs.readFileSync(srcpath));
        translate_field(field);
        fs.writeFileSync(dstpath, JSON.stringify(field, null, 2));
      });

      done();
    })().catch(err => {
      console.error(err);
      done(false);
    });
  });

  grunt.registerTask("verifyAppData", function() {
    let app_data = JSON.parse(fs.readFileSync("app/assets/data/appdata.json"));
    let var_map = JSON.parse(fs.readFileSync("app/assets/data_src/templates_descriptor.json"));

    let failures = [];

    function recordFailure(template_name, lang, text, msg) {
      let line = template_name + " : "+ lang + " : " + msg;
      failures.push(line);
    }

    function checkIfRightTagsUsed(variables, lang, text, template_name, expected_tags) {
      expected_tags.forEach(function(tag) {
        if (text.indexOf(tag) === -1) {
          recordFailure(template_name, lang, text, "missing expected tag: " + tag);
        }
      });
    }

    function checkForBrokenTags(variables, lang, text, template_name) {
      let open_b = (text.match(/{/g) || []).length;
      let close_b = (text.match(/{/g) || []).length;

      let tags = text.match(/{[A-Z][a-zA-Z]+}/g) || [];

      if (open_b !== close_b) {
        recordFailure(template_name, lang, text, "brackets misaligned");
      }
      if (open_b !== tags.length) {
        recordFailure(template_name, lang, text, "malformed tags");
      }

      // Check to see there are no other commonly used tags inside like: () [] %%, {{}}
      if (text.match(/\([A-Z][a-zA-Z]+\)/g) !== null ||
          text.match(/\[[A-Z][a-zA-Z]+/g) !== null ||
          text.match(/%[A-Z][a-zA-Z]+%/g) !== null ||
          text.match(/{{[A-Z][a-zA-Z]+}}/g) !== null) {
        recordFailure(template_name, lang, text, "mistaken variable tags");
      }

      tags.forEach(function(tag) {
        if (variables.indexOf(tag) < 0) {
          recordFailure(template_name, lang, text, "invalid tag " + tag);
        }
      });
    }

    // Check_for_missing_templates
    for (let template_name in var_map) {
      let lang_map = app_data["templates"][template_name];
      let variables = var_map[template_name];
      let expected_tags = (lang_map["en"].match(/{[A-Z][a-zA-Z]+}/g) || []);

      for (let lang in lang_map) {
        let text = lang_map[lang];
        checkIfRightTagsUsed(variables, lang, text, template_name, expected_tags);
        checkForBrokenTags(variables, lang, text, template_name);
      }
    }

    if (failures.length !== 0) {
      failures.forEach(function(failure) {
        console.log(failure);
      });

      grunt.fail.warn("verifyAppData task failure");
    } else {
      console.log("Successfully verified");
    }
  });

  // Run this task to push translations source on Weblate (no git access)
  grunt.registerTask("weblateUploadSource", function() {
    const done = this.async();

    uploadWeblateSourcePo(function(ok) {
      if (!ok) return done(false);
      console.log("Weblate: uploaded source " + sourceFile);
      done();
    });
  });

  // Run this task to fetch translations from Weblate (no git access)
  grunt.registerTask("weblateFetchTranslations", function() {
    const done = this.async();

    listWeblateTranslationsAllPages(function(err, items) {
      if (err) return done(false);

      let langsSet = {};
      items.forEach(function(it) {
        let code = extractLangCodeFromTranslationItem(it);
        if (code) langsSet[code] = true;
      });

      let langs = Object.keys(langsSet)
        .sort()
        .filter(function(c) { return c !== weblateSourceLang; });

      if (!langs.length) {
        console.log("Weblate: no languages found to download (besides source language).");
        return done();
      }

      let i = 0;
      let next = function() {
        if (i >= langs.length) return done();
        let lang = langs[i++];

        downloadWeblatePo(lang, function(err2, outPath) {
          if (err2) {
            console.log("Weblate: failed downloading " + lang + ": " + err2);
            return done(false);
          }
          console.log("Weblate: downloaded " + lang + " -> " + outPath);
          next();
        });
      };

      next();
    });
  });

  grunt.registerTask("pushTranslationsSource", ["confirm", "weblateUploadSource"]);

  grunt.registerTask("updateTranslations", ["weblateFetchTranslations", "makeAppData", "verifyAppData"]);

  grunt.registerTask("package", ["fetchFonts", "copy:build", "webpack", "string-replace", "postcss", "copy:package"]);

  grunt.registerTask("build", ["clean", "shell:build", "package", "shell:brotli_compress", "clean:tmp"]);

  grunt.registerTask("build_for_testing", ["clean", "shell:build_for_testing", "package", "shell:brotli_compress", "clean:tmp"]);

  grunt.registerTask("build_for_testing_and_instrument", ["clean", "shell:build_for_testing", "shell:instrument", "package", "shell:brotli_compress", "clean:tmp"]);
};

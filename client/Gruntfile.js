module.exports = function(grunt) {
  let fs = require("fs"),
      path = require("path"),
      superagent = require("superagent"),
      Gettext = require("node-gettext");

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
          {dest: "tmp/css/", cwd: "dist", src: ["styles-*"], expand: true, flatten: true},
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
            src: ['@fontsource/**/files/*400*', '@fontsource/**/files/*700*'],
            flatten: true,
            expand: true
          },
          {
            dest: 'build/fonts',
            cwd: 'node_modules/',
            src: ['@fortawesome/fontawesome-free/webfonts/*'],
            flatten: true,
            expand: true
          },
          {dest: "build/js", cwd: "tmp/js", src: ["**"], expand: true},
          {dest: "build/data", cwd: "tmp/assets/data", src: ["**"], expand: true},
          {dest: "build/viewer/", cwd: ".", src: ["app/viewer/*"], expand: true, flatten: true},
          {dest: "build/index.html", cwd: ".", src: ["tmp/index.html"], expand: false, flatten: true},
          {dest: "build/license.txt", cwd: ".", src: ["../LICENSE"], expand: false, flatten: true},
          {dest: "build/secret.html", cwd: ".", src: ["app/secret.html"], expand: false, flatten: true },
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
            "lib/js/locale/*.js",
            "secret.html"
          ],
          expand: true
        }]
      }
    },

    "string-replace": {
      pass1: {
        src: "./tmp/css/styles-*.css",
        dest: "./tmp/css/",
        options: {
          replacements: [
            {
              pattern: /(0056b3|007bff|17a2b8|28a745|34ce57)/gi,
              replacement: function () {
                return "2866a2";
              }
            },
            {
              pattern: /40, 167, 69/gi,
              replacement: function () {
                return "56,119,188";
              }
            },
            {
              pattern: /0069d9/gi,
              replacement: function () {
                return "377abc";
              }
            },
            {
              pattern: /cce5ff/gi,
              replacement: function () {
                return "eef5fc";
              }
            },
            {
              pattern: /005cbf/gi,
              replacement: function () {
                return "79b0e6";
              }
            },
            {
              pattern: /0062cc/gi,
              replacement: function () {
                return "9fc9f1";
              }
            },
            {
              pattern: /6c757d/gi,
              replacement: function () {
                return "58606e";
              }
            },
            {
              pattern: /5a6268/gi,
              replacement: function () {
                return "707a8a";
              }
            },
            {
              pattern: /4e555b/gi,
              replacement: function () {
                return "8e99aB";
              }
            },
            {
              pattern: /(545b62)/gi,
              replacement: function () {
                return "afbacc";
              }
            },
            {
              pattern: /(28a745|20c997)/gi,
              replacement: function () {
                return "2a854e";
              }
            },
            {
              pattern: /218838/gi,
              replacement: function () {
                return "3ba164";
              }
            },
            {
              pattern: /1e7e34/gi,
              replacement: function () {
                return "57c282";
              }
            },
            {
              pattern: /dc3545/gi,
              replacement: function () {
                return "b80d0d";
              }
            },
            {
              pattern: /c82333/gi,
              replacement: function () {
                return "de1b1b";
              }
            },
            {
              pattern: /b21f2d/gi,
              replacement: function () {
                return "fa8e8e";
              }
            },
            {
              pattern: /0.375rem/gi,
              replacement: function () {
                return "0.3rem";
              }
            },
            {
              pattern: /bd2130/gi,
              replacement: function () {
                return "fab6b6";
              }
            },
            {
              pattern: /(e9ecef|f8f9fa)/gi,
              replacement: function () {
                return "f5f7fa";
              }
            },
            {
              pattern: /(212529|343a40)/gi,
              replacement: function () {
                return "1d1f24";
              }
            },
            {
              pattern: /(#CED4DA|#DEE2E6|rgba\(0, 0, 0, \.125\))/gi,
              replacement: function () {
                return "#c8d1e0";
              }
            },
            {
              pattern: /(b8daff|d6d8db|c3e6cb|f5c6cb|ffeeba)/gi,
              replacement: function () {
                return "c8d1e0";
              }
            },
            {
              pattern: /155724|#383d41|721c24|856404/gi,
              replacement: function () {
                return "1d1f24";
              }
            },
            {
              pattern: /(#e2e3e5|rgba\(0, 0, 0, \.03\)|rgba\(0, 0, 0, \.05\))/gi,
              replacement: function () {
                return "#f5f7fa";
              }
            }
          ]
        }
      },

      pass2: {
        src: "./tmp/css/fonts.css",
        dest: "./tmp/css/",
        options: {
          replacements: [
            {
              pattern: /'fa-solid-/gi,
              replacement: function () {
                return "'../fonts/fa-solid-";
              }
            },
            {
              pattern: /url\(fa-/gi,
              replacement: function () {
                return "url(../fonts/fa-";
              }
            },
            {
              pattern: /url\(noto/gi,
              replacement: function () {
                return "url(../fonts/noto";
              }
            },
            {
              pattern: /url\(inter/gi,
              replacement: function () {
                return "url(../fonts/inter";
              }
            }
          ]
        }
      },

      pass3: {
        files: {
          "tmp/index.html": "tmp/index.html"
        },

        options: {
          replacements: [
            {
              pattern: /<script src="(\w+)\.js" type="module"><\/script>/g,
              replacement: '<script src="js/$1.js" type="module"></script>'
            },
            {
              pattern: /<link rel="stylesheet" href="/g,
              replacement: "<link rel=\"stylesheet\" href=\"css/"
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
              "this task may cause translations loss and should be executed only on main branch.\n\n" +
              "Are you sure you want to proceed (Y/N)?",
          input: "_key:y"
        }
      }
    },

    shell: {
      npx_build: {
        command: "npx ng build --configuration=production --aot --source-map"
      },
      npx_build_and_instrument: {
        command: "npx ng build --configuration=testing --source-map && nyc instrument dist instrument"
      },
      serve: {
        command: "ng serve --proxy-config proxy.conf.json"
      }
    },
  });

  grunt.loadNpmTasks("grunt-confirm");
  grunt.loadNpmTasks("grunt-contrib-clean");
  grunt.loadNpmTasks("grunt-contrib-copy");
  grunt.loadNpmTasks("grunt-shell");
  grunt.loadNpmTasks("grunt-string-replace");

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

  function readTransifexApiKey() {
    let keyfile = process.env.HOME + "/.transifexapikey";

    if (!fs.existsSync(keyfile)) {
      return "";
    }

    return grunt.file.read(keyfile).trim();
  }

  let agent = superagent.agent(),
      baseurl = "https://rest.api.transifex.com",
      sourceFile = "app/assets/data_src/pot/en.po",
      transifexApiKey = readTransifexApiKey();

  async function updateTxSource(cb) {
    const gettextParser = await loadGettextParser();
    let url = baseurl + "/resource_strings_async_uploads";

    let content = {
      "data": {
        "attributes": {
          "callback_url": null,
          "content": grunt.file.read(sourceFile),
          "content_encoding": "text",
          "replace_edited_strings": false
        },
        "relationships": {
          "resource": {
            "data": {
              "id": "o:otf:p:globaleaks:r:main",
              "type": "resources"
            }
          }
        },
        "type": "resource_strings_async_uploads"
      }
    };

    agent.post(url)
        .set({"Content-Type": "application/vnd.api+json", "Authorization": "Bearer " + transifexApiKey})
        .send(content)
        .end(function(err, res) {
          if (res) {
            if (res.ok) {
              cb();
            } else {
              console.log("Error: " + res.text);
            }
          } else {
            console.log("Error: failed to fetch resource " + url);
          }
        });
  }

  function listLanguages(cb) {
    let url = baseurl + "/projects/o:otf:p:globaleaks/languages";

    agent.get(url)
        .set({"Authorization": "Bearer " + transifexApiKey})
        .end(function(err, res) {
          if (res) {
            if (res.ok) {
              let result = JSON.parse(res.text);
              cb(result);
            } else {
              console.log("Error: " + res.text);
            }
          } else {
            console.log("Error: failed to fetch resource");
          }
        });
  }

  async function fetchTxTranslationsPO(langCode, cb) {
    const gettextParser = await loadGettextParser();
    let url = baseurl + "/resource_translations_async_downloads";

    agent.post(url)
        .set({"Authorization": "Bearer " + transifexApiKey, "Content-Type": "application/vnd.api+json"})
        .send({
          "data": {
            "attributes": {
              "content_encoding": "text",
              "file_type": "default",
              "mode": "default"
            },
            "relationships": {
              "language": {
                "data": {
                  "id": "l:" + langCode,
                  "type": "languages"
                }
              },
              "resource": {
                "data": {
                  "id": "o:otf:p:globaleaks:r:main",
                  "type": "resources"
                }
              }
            },
            "type": "resource_translations_async_downloads"
          }
        })
        .end(function(err, res) {
          if (res && res.ok) {
            url = JSON.parse(res.text).data.links.self;

            let fetchPO = function(url) {
              agent.get(url)
                  .set({"Authorization": "Bearer " + transifexApiKey})
                  .end(function(err, res) {
                    if (res && res.ok) {
                      if (res.redirects.length) {
                        let stream = fs.createWriteStream("app/assets/data_src/pot/" + langCode + ".po");

                        stream.on("finish", function () {
                          cb(true);
                        });

                        agent.get(res.redirects[0])
                            .set({"Authorization": "Bearer " + transifexApiKey})
                            .pipe(stream);

                      } else {
                        fetchPO(url);
                      }
                    } else {
                      console.log("Error: failed to fetch resource");
                      cb(false);
                    }
                  });
            };

            fetchPO(url);
          } else {
            console.log("Error: failed to fetch resource");
            cb(false);
          }
        });
  }

  async function fetchTxTranslationsForLanguage(langCode, cb) {
    const gettextParser = await loadGettextParser();
    let url = baseurl + "/resource_language_stats/o:otf:p:globaleaks:r:main:l:" + langCode;

    agent.get(url)
        .set({"Authorization": "Bearer " + transifexApiKey})
        .end(function(err, res) {
          if (res && res.ok) {
            let content = JSON.parse(res.text);

            // Add the new translations for languages translated above 50%
            if (content.data.attributes.translated_strings > content.data.attributes.untranslated_strings) {
              fetchTxTranslationsPO(langCode, cb);
            } else {
              cb(false);
            }
          } else {
            console.log("Error: failed to fetch resource");
            cb(false);
          }
        });
  }

  async function fetchTxTranslations(cb){
    let fetched_languages = 0,
        total_languages,
        supported_languages = {};

    listLanguages(function(result) {
      result.data = result.data.sort(function(a, b) {
        if (a.code > b.code) {
          return 1;
        }

        if (a.code < b.code) {
          return -1;
        }

        return 0;
      });

      total_languages = result.data.length;

      let fetchLanguage = function(language) {
        fetchTxTranslationsForLanguage(language.attributes.code, function(ret){
          if (ret) {
            console.log("Fetched " + language.attributes.code);
            supported_languages[language.attributes.code] = language.attributes.name;
          }

          fetched_languages += 1;

          if (total_languages === fetched_languages) {
            let sorted_keys = Object.keys(supported_languages).sort();

            console.log("List of available translations:");

            for (let i in sorted_keys) {
              console.log(" { \"code\": \"" + sorted_keys[i] +
                  "\", \"name\": \"" + supported_languages[sorted_keys[i]] +"\" },");
            }

            cb(supported_languages);
          } else {
            fetchLanguage(result.data[fetched_languages]);
          }
        });
      };

      fetchLanguage(result.data[0]);
    });
  }

  grunt.registerTask("makeTranslationsSource", async function() {
    const done = this.async();
    const gettextParser = await loadGettextParser();
    let data = {
      "charset": "UTF-8",
      "headers": {
        "project-id-version": "GlobaLeaks",
        "language-team": "English (http://www.transifex.com/otf/globaleaks/language/en/)",
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

    let gt = new Gettext(),
        translationStringRegexpJSON = /"en":\s?"(.+)"/gi;

    gt.setTextDomain("main");

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

  grunt.registerTask("☠☠☠pushTranslationsSource☠☠☠", function() {
    updateTxSource(this.async());
  });

  grunt.registerTask("fetchTranslations", function() {
    const done = this.async();  // Declare the async task
    (async () => {
      const gettextParser = await loadGettextParser();
      let gt = new Gettext(),
          lang_code;

      gt.setTextDomain("main");

      fetchTxTranslations(function(supported_languages) {
        // Parse and load the PO file
        gt.addTranslations("en", "main", gettextParser.po.parse(fs.readFileSync("app/assets/data_src/pot/en.po")));
        let strings = Object.keys(gettextParser.po.parse(fs.readFileSync("app/assets/data_src/pot/en.po"))["translations"][""]);

        // Process each supported language
        for (lang_code in supported_languages) {
          let translations = {}, output;

          gt.addTranslations(lang_code, "main", gettextParser.po.parse(fs.readFileSync("app/assets/data_src/pot/" + lang_code + ".po")));
          gt.setLocale(lang_code);

          for (let i = 0; i < strings.length; i++) {
            if (strings[i] === "") {
              continue;
            }

            translations[strings[i]] = str_unescape(gt.gettext(str_escape(strings[i])));
          }

          // Write translations to JSON files
          output = JSON.stringify(translations, null, 2);
          fs.writeFileSync("app/assets/data/l10n/" + lang_code + ".json", output);
        }

        // Ensure Grunt knows the task is finished
        done();
      });
    })().catch(err => {
      console.error(err);
      done(false);  // Signal error to Grunt
    });
  });

  grunt.registerTask("makeAppData", function() {
    const done = this.async();
    (async () => {
      const gettextParser = await loadGettextParser();
      let gt = new Gettext(),
          supported_languages = [];

      gt.setTextDomain("main");

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

      gt.addTranslations("en", "main", gettextParser.po.parse(fs.readFileSync("app/assets/data_src/pot/en.po")));

      grunt.file.recurse("app/assets/data_src/txt", function(absdir, rootdir, subdir, filename) {
        let template_name = filename.split(".txt")[0],
            filepath = path.join("app/assets/data_src/txt", subdir || "", filename || "");

        templates_sources[template_name] = grunt.file.read(filepath);
      });

      supported_languages.forEach(function(lang_code) {
        gt.setLocale(lang_code);
        gt.addTranslations(lang_code, "main", gettextParser.po.parse(fs.readFileSync("app/assets/data_src/pot/" + lang_code + ".po")));

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

  // Run this task to push translations on transifex
  grunt.registerTask("pushTranslationsSource", ["confirm", "☠☠☠pushTranslationsSource☠☠☠"]);

  // Run this task to fetch translations from transifex and create application files
  grunt.registerTask("updateTranslations", ["fetchTranslations", "makeAppData", "verifyAppData"]);

  grunt.registerTask("build", ["clean", "shell:npx_build", "copy:build", "string-replace", "copy:package", "clean:tmp"]);
 
  grunt.registerTask("build_and_instrument", ["clean", "shell:npx_build_and_instrument", "copy:build", "string-replace", "copy:package", "clean:tmp"]);
};


# Awesome List Template

This is an [awesome-list](https://github.com/sindresorhus/awesome) template with
CI to run [awesome-lint](https://github.com/sindresorhus/awesome-lint) and
[awesome_bot](https://github.com/dkhamsing/awesome_bot) to be compliant from the
beginning.

## Usage

1. [generate a template of this repo](https://github.com/jthegedus/awesome-list-template/generate)
2. run a find & replace of `YOUR_GITHUB_USER/YOUR_REPO` with your details
3. edit `readme-template.md`
   - update the h1 title
   - update the subtitle
   - update the description
   - add img src, make it link to the site of the thing in the image.
4. choose a CI template
   - GitHub Action: move config folder from `repo-root/ci/.github/` to
     `repo-root/.github`
   - Circle CI: move config folder from `repo-root/ci/.circleci/*` to
     `repo-root/.circleci/*`
   - GitLab CI: move config file from `repo-root/ci/.gitlab-ci.yml` to the
     `repo-root/.gitlab-ci.yml`
5. run a find & replace `readme-template.md` to `readme.md` in the CI you chose
5. delete this file
6. rename `readme-template.md` file to `readme.md`

## Contributing

Contributions welcome!

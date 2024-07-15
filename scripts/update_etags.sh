#!/bin/sh

etags \
      *.py *.sh *.txt *.md \
      src/*/*.py src/*/*.html src/*/*/*.js \
      tests/*.py tests/*/*.md tests/*/*.[ch]pp tests/*/*.py tests/*/*.sh \
      scripts/*.py scripts/*.sh scripts/*.awk \
      datas/*.py \
      tutorial/*.md tutorial/*/*.md

const gulp = require('gulp')
const minify = require('gulp-minify')

gulp.task('compress', function () {
  gulp.src('src/website/assets/*.js')
    .pipe(minify({
      ext: {
        src: '-debug.js',
        min: '.js'
      },
      exclude: ['tasks'],
      ignoreFiles: ['.combo.js', '-min.js']
    }))
    .pipe(gulp.dest('docs/assets'))
})

gulp.task('default', gulp.series(['compress']))

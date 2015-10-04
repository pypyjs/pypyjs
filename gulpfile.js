var gulp = require('gulp');
var sourcemaps = require('gulp-sourcemaps');
var babel = require('gulp-babel');
var eslint = require('gulp-eslint');
var wrapper = require('gulp-wrapper');
var gulpFilter = require('gulp-filter');

gulp.task('default', function def() {
  var filter = gulpFilter(['*', '!src/tests'], {restore: true});

  return gulp.src('src/**/*.js')
    .pipe(eslint())
    .pipe(sourcemaps.init())
    .pipe(babel())
    .pipe(eslint.format())
    .pipe(filter)
    .pipe(wrapper({
      header: '(function() {\n',
      footer: '\nreturn pypyjs;\n}());'
    }))
    .pipe(filter.restore)
    .pipe(sourcemaps.write('.'))
    .pipe(gulp.dest('lib'));
});

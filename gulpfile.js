var gulp = require('gulp');
var sourcemaps = require('gulp-sourcemaps');
var babel = require('gulp-babel');
var eslint = require('gulp-eslint');
var wrapper = require('gulp-wrapper');

gulp.task('default', function def() {
  return gulp.src('src/**/*.js')
    .pipe(eslint())
    .pipe(sourcemaps.init())
    .pipe(babel())
    .pipe(wrapper({
      header: '(function() {\n',
      footer: '\nreturn pypyjs;\n}());'
    }))
    .pipe(sourcemaps.write('.'))
    .pipe(gulp.dest('lib'));
});

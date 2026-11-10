#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static int valid_root(const char *root) {
  char resolved[PATH_MAX];
  struct stat st;
  if (!root || root[0] != '/' || !realpath(root, resolved) || strcmp(root, resolved) != 0 ||
      lstat(root, &st) != 0 || !S_ISDIR(st.st_mode) || S_ISLNK(st.st_mode)) {
    errno = EINVAL;
    return 0;
  }
  return 1;
}

static int valid_component(const char *value) {
  if (!value || !*value || strcmp(value, ".") == 0 || strcmp(value, "..") == 0 ||
      strchr(value, '/') || strchr(value, '\\')) {
    errno = EINVAL;
    return 0;
  }
  return 1;
}

static int redirected(const char *path, char out[PATH_MAX]) {
  const char *root = getenv("C17_MSGQ_ROOT");
  const char *prefix = getenv("OPENPILOT_PREFIX");
  static const char msgq_base[] = "/dev/shm/msgq_";
  if (!root || !*root || !path) return 0;
  if (strncmp(path, msgq_base, sizeof(msgq_base) - 1) != 0) return 0;
  if (!valid_root(root) || !valid_component(prefix)) return -1;

  char expected[PATH_MAX];
  int expected_len = snprintf(expected, sizeof(expected), "%s%s/", msgq_base, prefix);
  if (expected_len < 0 || expected_len >= (int)sizeof(expected) ||
      strncmp(path, expected, (size_t)expected_len) != 0) {
    errno = EINVAL;
    return -1;
  }
  const char *endpoint = path + expected_len;
  if (!valid_component(endpoint)) return -1;

  char namespace_path[PATH_MAX];
  int namespace_len = snprintf(namespace_path, sizeof(namespace_path), "%s/msgq_%s", root, prefix);
  char resolved_namespace[PATH_MAX];
  struct stat namespace_st;
  if (namespace_len < 0 || namespace_len >= (int)sizeof(namespace_path) ||
      !realpath(namespace_path, resolved_namespace) || strcmp(namespace_path, resolved_namespace) != 0 ||
      lstat(namespace_path, &namespace_st) != 0 || !S_ISDIR(namespace_st.st_mode) || S_ISLNK(namespace_st.st_mode)) {
    errno = EINVAL;
    return -1;
  }
  int n = snprintf(out, PATH_MAX, "%s/%s", namespace_path, endpoint);
  if (n < 0 || n >= PATH_MAX) { errno = ENAMETOOLONG; return -1; }
  return 1;
}

static int c17_shm_target(const char *name, char out[PATH_MAX]) {
  const char *root = getenv("C17_MSGQ_ROOT");
  if (!root || !*root || !name || strncmp(name, "/msgq_", 6) != 0) return 0;
  if (!valid_root(root) || name[0] != '/' || !valid_component(name + 1) ||
      !valid_component(name + 6)) {
    errno = EINVAL;
    return -1;
  }
  char event_path[PATH_MAX];
  char resolved_event[PATH_MAX];
  struct stat event_st;
  int event_len = snprintf(event_path, sizeof(event_path), "%s/event", root);
  if (event_len < 0 || event_len >= (int)sizeof(event_path) ||
      !realpath(event_path, resolved_event) || strcmp(event_path, resolved_event) != 0 ||
      lstat(event_path, &event_st) != 0 || !S_ISDIR(event_st.st_mode) || S_ISLNK(event_st.st_mode)) {
    errno = EINVAL;
    return -1;
  }
  int n = snprintf(out, PATH_MAX, "%s%s", event_path, name);
  if (n < 0 || n >= PATH_MAX) { errno = ENAMETOOLONG; return -1; }
  return 1;
}

static mode_t requested_mode(int flags, va_list ap) {
  return (flags & O_CREAT) ? va_arg(ap, mode_t) : 0;
}

int open(const char *path, int flags, ...) {
  static int (*real_open)(const char *, int, ...) = NULL;
  if (!real_open) real_open = dlsym(RTLD_NEXT, "open");
  va_list ap;
  va_start(ap, flags);
  mode_t mode = requested_mode(flags, ap);
  va_end(ap);
  char target[PATH_MAX];
  int use = redirected(path, target);
  if (use < 0) return -1;
  const char *actual = use ? target : path;
  int actual_flags = use ? flags | O_NOFOLLOW : flags;
  return (actual_flags & O_CREAT) ? real_open(actual, actual_flags, mode) : real_open(actual, actual_flags);
}

int open64(const char *path, int flags, ...) {
  static int (*real_open64)(const char *, int, ...) = NULL;
  if (!real_open64) real_open64 = dlsym(RTLD_NEXT, "open64");
  va_list ap;
  va_start(ap, flags);
  mode_t mode = requested_mode(flags, ap);
  va_end(ap);
  char target[PATH_MAX];
  int use = redirected(path, target);
  if (use < 0) return -1;
  const char *actual = use ? target : path;
  int actual_flags = use ? flags | O_NOFOLLOW : flags;
  return (actual_flags & O_CREAT) ? real_open64(actual, actual_flags, mode) : real_open64(actual, actual_flags);
}

int shm_open(const char *name, int oflag, mode_t mode) {
  static int (*real_open)(const char *, int, ...) = NULL;
  if (!real_open) real_open = dlsym(RTLD_NEXT, "open");
  char target[PATH_MAX];
  int use = c17_shm_target(name, target);
  if (use < 0) return -1;
  if (!use) {
    static int (*real_shm_open)(const char *, int, mode_t) = NULL;
    if (!real_shm_open) real_shm_open = dlsym(RTLD_NEXT, "shm_open");
    return real_shm_open(name, oflag, mode);
  }
  return real_open(target, oflag | O_NOFOLLOW, mode);
}

int shm_unlink(const char *name) {
  char target[PATH_MAX];
  int use = c17_shm_target(name, target);
  if (use < 0) return -1;
  if (!use) {
    static int (*real_shm_unlink)(const char *) = NULL;
    if (!real_shm_unlink) real_shm_unlink = dlsym(RTLD_NEXT, "shm_unlink");
    return real_shm_unlink(name);
  }
  return unlink(target);
}

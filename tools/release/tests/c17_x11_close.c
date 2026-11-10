#include <X11/Xatom.h>
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static Window find_named(Display *dpy, Window root, const char *needle) {
  Window parent, *children = NULL;
  unsigned int nchildren = 0;
  char *name = NULL;
  if (XFetchName(dpy, root, &name) && name != NULL) {
    int match = strstr(name, needle) != NULL;
    XFree(name);
    if (match) return root;
  }
  if (!XQueryTree(dpy, root, &root, &parent, &children, &nchildren)) return 0;
  for (unsigned int i = 0; i < nchildren; i++) {
    Window found = find_named(dpy, children[i], needle);
    if (found) { if (children) XFree(children); return found; }
  }
  if (children) XFree(children);
  return 0;
}

int main(int argc, char **argv) {
  if (argc != 2) return 64;
  Display *dpy = XOpenDisplay(NULL);
  if (!dpy) return 69;
  Window win = find_named(dpy, DefaultRootWindow(dpy), argv[1]);
  if (!win) { XCloseDisplay(dpy); return 1; }
  Atom wm_delete = XInternAtom(dpy, "WM_DELETE_WINDOW", False);
  Atom wm_protocols = XInternAtom(dpy, "WM_PROTOCOLS", False);
  XEvent event;
  memset(&event, 0, sizeof(event));
  event.xclient.type = ClientMessage;
  event.xclient.window = win;
  event.xclient.message_type = wm_protocols;
  event.xclient.format = 32;
  event.xclient.data.l[0] = wm_delete;
  event.xclient.data.l[1] = CurrentTime;
  Status sent = XSendEvent(dpy, win, False, NoEventMask, &event);
  XFlush(dpy);
  XCloseDisplay(dpy);
  return sent ? 0 : 1;
}

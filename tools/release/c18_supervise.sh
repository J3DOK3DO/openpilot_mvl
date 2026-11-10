#!/usr/bin/env bash
# Sourced by the target launcher; separately exercised by lifecycle regressions.
c18_supervise() {
  local runtime_dir=$1
  shift
  [[ $runtime_dir == /tmp/c18-display.* && -d $runtime_dir && ! -L $runtime_dir ]] || {
    echo "unsafe C18 runtime directory" >&2
    return 70
  }
  local ui_pid=
  local forwarded_signal=
  c18_cleanup() {
    trap - EXIT INT TERM HUP
    if [[ -n $ui_pid ]]; then
      if kill -0 "$ui_pid" 2>/dev/null; then
        kill -TERM "$ui_pid" 2>/dev/null || true
      fi
      wait "$ui_pid" 2>/dev/null || true
    fi
    rm -rf -- "$runtime_dir"
  }
  c18_forward_signal() {
    local sig=$1
    forwarded_signal=$sig
    if [[ -n $ui_pid ]] && kill -0 "$ui_pid" 2>/dev/null; then
      kill -s "$sig" "$ui_pid" 2>/dev/null || true
    fi
  }
  trap c18_cleanup EXIT
  trap 'c18_forward_signal TERM' TERM
  trap 'c18_forward_signal INT' INT
  trap 'c18_forward_signal HUP' HUP
  "$@" &
  ui_pid=$!
  set +e
  local ui_status=0
  while kill -0 "$ui_pid" 2>/dev/null; do
    wait "$ui_pid"
    ui_status=$?
    # A trapped signal interrupts wait before the child necessarily completes
    # its own handler. Re-wait until the child has actually terminated.
  done
  wait "$ui_pid" 2>/dev/null
  local final_status=$?
  if [[ $final_status -ne 127 ]]; then
    ui_status=$final_status
  fi
  c18_cleanup
  trap - EXIT INT TERM HUP
  set -e
  if [[ -n $forwarded_signal ]]; then
    return 143
  fi
  return "$ui_status"
}

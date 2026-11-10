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
  local watchdog_pid=
  local watchdog_expired=0
  local forwarded_signal=
  local runtime_limit=${C18_SUPERVISOR_TIMEOUT_SECONDS:-120}
  local kill_grace=${C18_SUPERVISOR_KILL_GRACE_SECONDS:-5}
  [[ $runtime_limit =~ ^[0-9]+$ && $runtime_limit -ge 1 && $runtime_limit -le 3600 ]] || {
    echo "invalid C18 supervisor timeout" >&2
    return 64
  }
  [[ $kill_grace =~ ^[0-9]+$ && $kill_grace -ge 1 && $kill_grace -le 30 ]] || {
    echo "invalid C18 supervisor kill grace" >&2
    return 64
  }
  c18_stop_child() {
    local initial_signal=${1:-TERM}
    local remaining=$kill_grace
    if [[ -n $ui_pid ]] && kill -0 "$ui_pid" 2>/dev/null; then
      kill -s "$initial_signal" "$ui_pid" 2>/dev/null || true
      while [[ $remaining -gt 0 ]] && kill -0 "$ui_pid" 2>/dev/null; do
        sleep 1
        remaining=$((remaining - 1))
      done
      if kill -0 "$ui_pid" 2>/dev/null; then
        kill -KILL "$ui_pid" 2>/dev/null || true
      fi
    fi
    if [[ -n $ui_pid ]]; then
      wait "$ui_pid" 2>/dev/null || true
    fi
  }
  c18_cleanup() {
    trap - EXIT INT TERM HUP
    if [[ -n $watchdog_pid ]] && kill -0 "$watchdog_pid" 2>/dev/null; then
      kill -TERM "$watchdog_pid" 2>/dev/null || true
      wait "$watchdog_pid" 2>/dev/null || true
    fi
    c18_stop_child
    rm -rf -- "$runtime_dir"
  }
  c18_forward_signal() {
    local sig=$1
    forwarded_signal=$sig
    c18_stop_child "$sig"
  }
  trap c18_cleanup EXIT
  trap 'c18_forward_signal TERM' TERM
  trap 'c18_forward_signal INT' INT
  trap 'c18_forward_signal HUP' HUP
  "$@" &
  ui_pid=$!
  (
    timer_pid=
    stop_timer() {
      if [[ -n $timer_pid ]]; then
        kill -TERM "$timer_pid" 2>/dev/null || true
        wait "$timer_pid" 2>/dev/null || true
      fi
      exit 0
    }
    trap stop_timer TERM INT HUP
    sleep "$runtime_limit" &
    timer_pid=$!
    wait "$timer_pid" || exit 0
    if kill -0 "$ui_pid" 2>/dev/null; then
      : > "$runtime_dir/.watchdog-expired"
      kill -TERM "$ui_pid" 2>/dev/null || true
      sleep "$kill_grace" &
      timer_pid=$!
      wait "$timer_pid" || exit 0
      if kill -0 "$ui_pid" 2>/dev/null; then
        kill -KILL "$ui_pid" 2>/dev/null || true
      fi
    fi
  ) &
  watchdog_pid=$!
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
  if [[ -n $watchdog_pid ]]; then
    kill -TERM "$watchdog_pid" 2>/dev/null || true
    wait "$watchdog_pid" 2>/dev/null || true
    watchdog_pid=
  fi
  if [[ -e $runtime_dir/.watchdog-expired ]]; then
    watchdog_expired=1
  fi
  c18_cleanup
  trap - EXIT INT TERM HUP
  set -e
  if [[ -n $forwarded_signal ]]; then
    return 143
  fi
  if [[ $watchdog_expired -eq 1 ]]; then
    return 124
  fi
  return "$ui_status"
}

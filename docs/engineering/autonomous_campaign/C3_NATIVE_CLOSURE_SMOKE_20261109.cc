#include "openpilot/cereal/messaging/messaging.h"

// Link-only probe. This binary is never executed.
int main() {
  SubMaster subscriber({});
  PubMaster publisher({});
  return subscriber.frame == 0 ? 0 : 1;
}

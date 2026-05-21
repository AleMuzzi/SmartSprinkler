enum Action {
  STOP,
  START,
  DISPENSE_SPECIFIC_AMOUNT;
}

enum Target {
  NAGA_MORICH,
  ROSMARINO,
  HABANERO,
  CAROLINA_REAPER,
}

class Command {
  final Action action;
  final Target target;  // target plant
  final int amount; // in milliliters (only valid if action is DISPENSE_SPECIFIC_AMOUNT)
  final bool force; // bypass water-low guard

  const Command({required this.action, required this.target, this.amount = 0, this.force = false});

  String toJson() {
    return '{"action": "${action.name}", "target": "${target.name}", "amount": $amount, "force": $force}';
  }
}
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

  const Command({required this.action, required this.target, this.amount = 0});

  String toJson() {
    return '{"action": "${action.name}", "target": "${target.name}", "amount": $amount}';
  }
}
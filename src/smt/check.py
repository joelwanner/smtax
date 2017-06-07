from network.execution import Execution
from network.network import *
from smt.encode import ModelEncoder
from smt.decode import ModelDecoder
from smt.solve import *


class AttackChecker:
    def __init__(self, network, n_flows, victims=None, links=None, attackers=None):
        if n_flows <= 0:
            raise ValueError("Invalid number of flows specified")

        self.network = network
        self.n_flows = n_flows
        self.victims = victims
        self.target_links = links
        self.attackers = attackers

        self.attacks = []
        self.verbose = False

    def __check_execution(self, execution):
        encoder = ModelEncoder(execution, self.n_flows)
        assertions = encoder.get_assertions()

        solver = SmtSolver(verbose=self.verbose)
        result = solver.solve(assertions)

        if result == sat:
            decoder = ModelDecoder(encoder.model, solver.model)
            execution.flows = decoder.flows()
            execution.victims = decoder.victims()
            execution.attackers = decoder.attackers()

            return execution
        else:
            return None

    def check_host_attacks(self):
        if not self.attackers:
            potential_attackers = [h for h in self.network.hosts if not (isinstance(h, Server) or h == self.victims)]
        else:
            potential_attackers = self.attackers

        # Single victim is specified
        if self.victims and len(self.victims) == 1:
            # Check attack on single victim
            attack = self.__check_execution(Execution(self.network, self.n_flows, self.victims, potential_attackers))
            if attack:
                self.attacks.append(attack)
                return [attack]
            else:
                return []

        # Multiple or no victims are specified
        else:
            if self.victims:
                potential_victims = list(self.victims)
            else:
                if self.attackers:
                    potential_victims = list([h for h in self.network.hosts if h not in self.attackers])
                else:
                    potential_victims = list(self.network.hosts)

            while potential_victims:
                # Perform first check to see which hosts can be attacked
                print("Looking for attacks on %s" % potential_victims)
                e = Execution(self.network, self.n_flows, potential_victims, self.attackers)
                attack = self.__check_execution(e)

                if attack:
                    print("Potential victims: %s" % attack.victims)
                    if len(attack.victims) == 1:
                        self.attacks.append(attack)
                        potential_victims.remove(attack.victims[0])
                    else:
                        # For more than one victim, there may be an attack possible -- check them individually
                        for v in attack.victims:
                            potential_victims.remove(v)
                            print("Checking attack on victim %s" % v.__repr__())

                            attackers = [h for h in potential_attackers if h != v]
                            attack = self.__check_execution(Execution(self.network, self.n_flows, [v], attackers))

                            if attack:
                                self.attacks.append(attack)
                else:
                    break

            return self.attacks

    def check_link_attack(self):
        if not self.attackers:
            potential_attackers = [h for h in self.network.hosts if not (isinstance(h, Server) or h == self.victims)]
        else:
            potential_attackers = self.attackers

        attack = self.__check_execution(Execution(self.network, self.n_flows, self.target_links, potential_attackers))

        if attack:
            return [attack]
        else:
            return []

    @classmethod
    def from_string(cls, s, n_flows):
        return parser.parse_attack(s, n_flows)

    @classmethod
    def from_execution(cls, e, n_flows):
        victim_hosts = [h for h in e.victims if isinstance(h, Host)]
        victim_links = [h for h in e.victims if isinstance(h, Link)]
        return cls(e.network, n_flows, victim_hosts, victim_links, e.attackers)

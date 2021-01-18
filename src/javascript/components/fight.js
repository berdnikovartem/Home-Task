import { controls } from '../../constants/controls';
import { setFighterHealthBar, playSound, showIconHit } from './fightEffects';

export async function fight(firstFighter, secondFighter) {
  return new Promise((resolve) => {
    let fighterOne = {
      fighter: firstFighter,
      health: firstFighter.health,
      blockCriticalHit: false,
      indicator: document.getElementById('left-fighter-indicator')
    };
    let fighterTwo = {
      fighter: secondFighter,
      health: secondFighter.health,
      blockCriticalHit: false,
      indicator: document.getElementById('right-fighter-indicator')
    };
    let pressedKeys = new Set();

    document.addEventListener('keydown', (event) => {
      pressedKeys.add(event.code);

      switch (event.code) {
        case controls.PlayerOneAttack:
          if (!pressedKeys.has(controls.PlayerOneBlock) && !pressedKeys.has(controls.PlayerTwoBlock)) {
            strike(fighterOne, fighterTwo);
          }
          if (pressedKeys.has(controls.PlayerTwoBlock)) {
            playSound('block');
            showIconHit(fighterTwo, 'block');
          }
          break;
        case controls.PlayerTwoAttack:
          if (!pressedKeys.has(controls.PlayerTwoBlock) && !pressedKeys.has(controls.PlayerOneBlock)) {
            strike(fighterTwo, fighterOne);
          }
          if (pressedKeys.has(controls.PlayerOneBlock)) {
            playSound('block');
            showIconHit(fighterOne, 'block');
          }
          break;
      }

      if (!fighterOne.blockCriticalHit &&
          controls.PlayerOneCriticalHitCombination.includes(event.code) &&
          checkKeysCriticalHit(controls.PlayerOneCriticalHitCombination, pressedKeys)) {
        strike(fighterOne, fighterTwo, true);
      }
      if (!fighterTwo.blockCriticalHit &&
          controls.PlayerTwoCriticalHitCombination.includes(event.code) &&
          checkKeysCriticalHit(controls.PlayerTwoCriticalHitCombination, pressedKeys)) {
        strike(fighterTwo, fighterOne, true);
      }
    });

    document.addEventListener('keyup', (event) => {
      pressedKeys.delete(event.code);
    });

    function strike(attacker, defender, isCritical = false) {
      let damage;
      if (isCritical) {
        playSound('crit');
        showIconHit(defender, 'crit');
        damage = getCriticalDamage(attacker.fighter);
        attacker.blockCriticalHit = true;
        setTimeout(() => {
          attacker.blockCriticalHit = false;
        }, 10000);
      } else {
        playSound('hit');
        showIconHit(defender, 'hit');
        damage = getDamage(attacker.fighter, defender.fighter);
      }
      defender.health -= damage;
      setFighterHealthBar(defender);
      if (defender.health <= 0) resolve(attacker.fighter);
    }
  });
}

export function getDamage(attacker, defender) {
  const hitPower = getHitPower(attacker);
  const blockPower = getBlockPower(defender);
  let damage = hitPower - blockPower;
  damage = damage > 0 ? damage : 0;
  return damage;
}

export function getCriticalDamage(attacker) {
  const damage = attacker.attack * 2;
  return damage;
}

export function getHitPower(fighter) {
  const criticalHitChance = Math.random() + 1;
  const power = fighter.attack * criticalHitChance;
  return power;
}

export function getBlockPower(fighter) {
  const dodgeChance = Math.random() + 1;
  const power = fighter.defense * dodgeChance;
  return power;
}

function checkKeysCriticalHit(keys, pressed) {
  for (let key of keys) {
    if (!pressed.has(key)) {
      return false;
    }
  }
  return true;
}

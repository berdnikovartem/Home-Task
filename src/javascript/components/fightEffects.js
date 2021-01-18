export function setFighterHealthBar(player) {
  let percent = player.health * 100 / player.fighter.health;
  if (percent < 0) percent = 0;
  player.indicator.style.width = `${percent}%`;
}

export function playSound(type = 'hit') {
  let src = './resources/hit.mp3';
  if (type === 'crit') src = './resources/crit.mp3';
  if (type === 'block') src = './resources/block.mp3';
  const audio = new Audio();
  audio.src = src;
  audio.autoplay = true;
}

export function showIconHit(fighter, type = 'hit') {
  let cls = 'arena___health-hit';
  if (type === 'crit') cls = 'arena___health-crit';
  if (type === 'block') cls = 'arena___health-block';
  fighter.indicator.classList.add(cls);
  setTimeout(() => {fighter.indicator.classList.remove(cls)}, 200);
}

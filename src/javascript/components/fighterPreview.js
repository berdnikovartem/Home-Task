import { createElement } from '../helpers/domHelper';

export function createFighterPreview(fighter, position) {
  const positionClassName = position === 'right' ? 'fighter-preview___right' : 'fighter-preview___left';
  const fighterElement = createElement({
    tagName: 'div',
    className: `fighter-preview___root ${positionClassName}`,
  });

  if (fighter) {
    const image = createFighterImage(fighter);
    const info = createFighterInfo(fighter);
    fighterElement.append(image, info);
  } else if (fighter === false) {
    const error = createLoadErrorElement('Failed to load fighter 😪');
    fighterElement.append(error);
  }

  return fighterElement;
}

export function createFighterImage(fighter) {
  const { source, name } = fighter;
  const attributes = { 
    src: source, 
    title: name,
    alt: name 
  };
  const imgElement = createElement({
    tagName: 'img',
    className: 'fighter-preview___img',
    attributes,
  });

  return imgElement;
}

function createFighterInfo(fighter) {
  const info = createElement({
    tagName: 'div',
    className: 'fighter-preview___info'
  });
  const name = createElement({
    tagName:'h2',
    className: 'fighter-preview___info-name'
  });
  name.innerText = fighter.name;
  const health = createFighterInfoElement('❤️ Health', fighter.health);
  const attack = createFighterInfoElement('⚔️ Attack', fighter.attack);
  const defense = createFighterInfoElement('🛡️ Defense', fighter.defense);
  info.append(name, health,attack,defense);
  return info;
}

function createFighterInfoElement(name, value) {
  const element = createElement({
    tagName: 'div',
    className: 'fighter-preview___info-row'
  });
  const nameElement = createElement({tagName: 'span'});
  nameElement.innerText = `${name}:`;
  const valueElement = createElement({tagName: 'span'})
  valueElement.innerText = value;
  element.append(nameElement, valueElement);
  return element;
}

function createLoadErrorElement(textError) {
  const element = createElement({
    tagName: 'div',
    className: 'fighter-preview___info fighter-preview___load-error'
  });
  element.innerText = textError;
  return element;
}

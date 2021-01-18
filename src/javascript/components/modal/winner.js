import { showModal } from './modal';
import { createElement } from '../../helpers/domHelper';
import { createFighterImage } from '../fighterPreview';
import App from '../../app';

export function showWinnerModal(fighter) {
  const title = `Winner ${fighter.name}`;
  const bodyElement = createFighter(fighter);
  showModal({
    title,
    bodyElement,
    onClose
  });
}

function createFighter(fighter) {
  const imgElement = createFighterImage(fighter);
  const fighterElement = createElement({
    tagName: 'div',
    className: 'arena___fighter'
  });

  fighterElement.append(imgElement);
  return fighterElement;
}

function onClose() {
  const arena = document.querySelector('.arena___root');
  arena.remove();
  new App();
}

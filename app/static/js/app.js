document.querySelector('.menu')?.addEventListener('click',()=>document.querySelector('.sidebar')?.classList.toggle('open'));
document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-tab]').forEach(item=>item.classList.remove('active'));
  document.querySelectorAll('[data-panel]').forEach(item=>item.classList.remove('active'));
  button.classList.add('active');
  document.querySelector(`[data-panel="${button.dataset.tab}"]`)?.classList.add('active');
}));
document.querySelectorAll('[data-form-tab]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-form-tab]').forEach(item=>item.classList.remove('active'));
  document.querySelectorAll('[data-form-panel]').forEach(item=>item.classList.remove('active'));
  button.classList.add('active');
  document.querySelector(`[data-form-panel="${button.dataset.formTab}"]`)?.classList.add('active');
}));
document.querySelector('#workbook')?.addEventListener('change',event=>{
  const name=event.target.files?.[0]?.name||'No file selected';
  const target=document.querySelector('[data-file-name]');
  if(target) target.textContent=name;
});
document.querySelector('[data-add-line]')?.addEventListener('click',()=>{
  const template=document.querySelector('#line-template');
  if(template) document.querySelector('[data-line-items]')?.append(template.content.cloneNode(true));
});
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-remove-line]');
  if(!button) return;
  const rows=document.querySelectorAll('[data-line-items] .line-row');
  if(rows.length>1) button.closest('.line-row')?.remove();
});

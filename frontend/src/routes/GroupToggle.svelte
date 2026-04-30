<script lang="ts">
  export let checked = true;
  export let label = 'Group nodes';
</script>

<label style="display: flex; align-items: center; gap: 5px; font-size: 11px; cursor: pointer; user-select: none;">
  <input
    type="checkbox"
    bind:checked
    style="cursor: pointer;"
  />
  {label}
</label>
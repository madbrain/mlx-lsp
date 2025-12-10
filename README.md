
# MLX LSP Server

Watching videos from [C64 Appreciation Society](https://www.youtube.com/watch?v=3I7Lx3dbtRg&t=455s),
I also wanted to have a go in typing old video games but with modern tools!

This [LSP](https://microsoft.github.io/language-server-protocol/) Server allows to validate a file in MLX II format as you type.

## Install

Define a new file type by writing the file `$HOME/.config/nvim/ftdetect/mlx.vim`:
```vim
au BufRead,BufNewFile *.mlx		set filetype=mlx
```

And add to `$HOME/.config/nvim/init.lua`:
```lua
vim.lsp.config('mlx', {
  cmd = { "uv", "run",
     "--project", "/home/ludo/Decompilation/Crown_Quest/lsp",
     "/home/ludo/Decompilation/Crown_Quest/lsp/main.py"
  },
  filetypes = {'mlx'},
})
vim.lsp.enable('mlx')
```

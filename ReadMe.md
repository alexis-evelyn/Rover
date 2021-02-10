### OSX

* Python 3.9+ Is Required

```bash
sudo port install python39 py39-pip py39-setuptools py39-setuptools py39-psycopg2 openssl freetype
# sudo port install py39-numpy # (OR) brew install openblas

sudo port select --set python3 python39
sudo port select --set pip3 pip39

# Instructions For Variables
# https://stackoverflow.com/a/65072442/6828099
# https://stackoverflow.com/a/60748789/6828099

export PATH=/opt/local/lib/postgresql13/bin/:$PATH
export LDFLAGS="-L/opt/local/lib"
export CPPFLAGS="-I/opt/local/include"

# You may need to specify --no-cache-dir after install
pip3 install -r requirements.txt
```

### RPi

```bash
# Install Python 3.9
cd /usr/src

# Download and Extract Python 3.9
sudo wget https://www.python.org/ftp/python/3.9.1/Python-3.9.1.tgz
sudo tar xvf Python-3.9.1.tgz

# Install Build Tools
sudo apt-get update
sudo apt-get install -y build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev

# Build Python 3.9
cd Python-3.9.1
sudo ./configure --enable-optimizations
sudo make altinstall

# Symlink Python (You May Need To Add /usr/local/bin/ To Your Executable Path)
sudo ln -s /usr/local/bin/python3.9 /usr/local/bin/python
sudo ln -s /usr/local/bin/python3.9 /usr/local/bin/python3

# OPTIONAL (Disable Built In Python)
sudo chmod -x /usr/bin/python
sudo chmod -x /usr/bin/python3

# Install Pip, Wheel, and SetupTools
python3 -m pip install --upgrade pip setuptools wheel

# Install postgres-dev For psycopg2
sudo apt-get install libpq-dev

# You may need to specify --no-cache-dir after install
pip3 install -r requirements.txt
```

### Deprecated RPI Instructions (Due To 3.7 Being The Latest Release and Requirement For 3.9+)

```bash
# Install Missing Libraries
sudo apt-get install libfreetype6-dev libopenjp2-7 libtiff5

# You may need to specify --no-cache-dir after install
pip3 install -r requirements.txt
```

<!-- DeepNote Notebook Tutorial - https://www.dolthub.com/blog/2020-10-14-using-dolt-with-deepnote/ -->
<!-- `apt install libmariadb-dev` For DeepNote Notebook -->
<!-- https://web.archive.org/web/*/twitter.com/realdonaldtrump -->
<!-- https://web.archive.org/web/*/twitter.com/potus -->
<!-- tensorflow>=2.4.0 -->
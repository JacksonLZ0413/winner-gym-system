const app = getApp()

Page({
  data: {
    username: '',
    password: '',
    loading: false
  },

  onUsernameInput: function(e) {
    this.setData({
      username: e.detail.value
    })
  },

  onPasswordInput: function(e) {
    this.setData({
      password: e.detail.value
    })
  },

  doLogin: function() {
    const { username, password } = this.data
    if (!username || !password) {
      wx.showToast({ title: '请输入用户名和密码', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    
    app.request({
      url: '/login',
      method: 'POST',
      data: { username, password },
      noAuth: true
    }).then((data) => {
      app.globalData.token = data.token
      app.globalData.userInfo = data.user
      wx.setStorageSync('token', data.token)
      wx.setStorageSync('userInfo', data.user)
      wx.showToast({ title: '登录成功', icon: 'success' })
      setTimeout(() => {
        wx.switchTab({
          url: '/pages/my/my'
        })
      }, 1500)
    }).catch((err) => {
      wx.showToast({ title: err, icon: 'none' })
    }).finally(() => {
      this.setData({ loading: false })
    })
  },

  goToRegister: function() {
    wx.navigateTo({
      url: '/pages/register/register'
    })
  }
})
